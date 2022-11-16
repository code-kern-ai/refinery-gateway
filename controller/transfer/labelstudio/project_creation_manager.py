import json
from typing import Dict, Any, List, Tuple

from controller.transfer.labelstudio.util import create_unknown_users
from controller.transfer.record_transfer_manager import download_file
from submodules.model import enums, events
from submodules.model.business_objects import (
    upload_task,
    attribute,
    labeling_task,
    record,
    record_label_association,
    labeling_task_label,
    general,
    project,
)
from controller.upload_task import manager as upload_task_manager
from util import doc_ock
from controller.user import manager as user_manager


def manage_data_import(project_id: str, task_id: str) -> None:
    task = upload_task.get(project_id, task_id)
    file_path = download_file(project_id, task)
    mappings = json.loads(task.mappings)
    user_mapping = mappings.get("users")
    user_mapping = create_unknown_users(user_mapping)
    attribute_task_mapping = mappings.get("tasks")
    with open(file_path) as file:
        data = json.load(file)

        first_record_item = data[0]
        for attribute_name, attribute_value in first_record_item.get("data").items():
            __create_attribute(project_id, attribute_name, attribute_value)

        labeling_tasks, records, record_label_associations = __extract_data(
            data, user_mapping, attribute_task_mapping
        )
        label_id_lookup = __create_labeling_tasks(project_id, labeling_tasks)
        __create_records(
            project_id, records, record_label_associations, label_id_lookup
        )
        number_records = len(records)

    upload_task_manager.update_upload_task_to_finished(task)
    upload_task_manager.update_task(
        project_id, task.id, state=enums.UploadStates.DONE.value, progress=100.0
    )

    user = user_manager.get_or_create_user(task.user_id)
    project_item = project.get(project_id)
    doc_ock.post_event(
        user,
        events.UploadRecords(
            ProjectName=f"{project_item.name}-{project_item.id}", Records=number_records
        ),
    )
    general.commit()


def __create_records(
    project_id: str,
    records: List[Dict],
    record_label_associations: List[Dict],
    label_id_lookup: Dict,
) -> None:
    record_mapping_dict = {}

    for record_item in records:
        created_record = record.create(project_id, record_item.get("data"), "SCALE")
        record_mapping_dict[record_item.get("label_studio_id")] = str(created_record.id)

        for association_item in record_label_associations.get(
            record_item.get("label_studio_id")
        ):
            record_label_association.create(
                project_id,
                created_record.id,
                labeling_task_label_id=label_id_lookup.get(
                    association_item.get("labeling_task")
                ).get(association_item.get("label")),
                created_by=association_item.get("created_by"),
                source_type=enums.LabelSource.MANUAL.value,
                return_type=enums.InformationSourceReturnType.RETURN.value,
                is_gold_star=False,
            )


def __create_labeling_tasks(project_id: str, labeling_tasks: Dict[str, Any]) -> Dict:
    label_id_lookup = {}

    attribute_ids_by_names = {
        item.name: str(item.id) for item in attribute.get_all(project_id)
    }

    for task_name, task_data in labeling_tasks.items():
        task = labeling_task.create(
            project_id,
            attribute_ids_by_names.get(
                task_data.get("attribute"),
            ),
            task_name,
            task_target=__infer_target(task_data.get("attribute")),
            task_type=enums.LabelingTaskType.CLASSIFICATION.value,
        )
        label_id_lookup[task.name] = {}
        for label in task_data.get("labels"):
            label_item = labeling_task_label.create(project_id, label, task.id)
            label_id_lookup[task.name][label] = label_item.id

    return label_id_lookup


def __infer_target(target_attribute: str) -> str:
    return (
        enums.LabelingTaskTarget.ON_ATTRIBUTE.value
        if target_attribute
        else enums.LabelingTaskTarget.ON_WHOLE_RECORD.value
    )


def __extract_data(data: Any, user_mapping: Dict, attribute_task_mapping: Dict) -> Tuple[Dict, List, Dict]:
    labeling_tasks = {}
    records = []
    record_label_associations = {}
    for record_item in data:
        record = {
            "label_studio_id": record_item.get("id"),
            "data": record_item.get("data"),
        }
        record_label_associations[record_item.get("id")] = []

        for annotation_item in record_item.get("annotations"):
            for result in annotation_item["result"]:

                record_label_association = {
                    "created_by": "",
                    "label": "",
                    "labeling_task": "",
                    "record_id": "",
                }

                if (
                    user_mapping.get(str(annotation_item.get("completed_by")))
                    == enums.RecordImportMappingValues.IGNORE.value
                ):
                    continue

                if result.get("type") != "choices":
                    continue

                if len(result.get("value").get("choices")) > 1:
                    continue

                task_name = result.get("from_name")
                if not labeling_tasks.get(task_name):
                    labeling_tasks[task_name] = {"labels": set()}

                if (
                    attribute_task_mapping.get(task_name)
                    == enums.RecordImportMappingValues.ATTRIBUTE_SPECIFIC.value
                ):
                    labeling_tasks.get(task_name)["attribute"] = result.get("to_name")

                label = result.get("value").get("choices")[0]
                labeling_tasks.get(task_name)["labels"].add(label)

                created_by = user_mapping.get(str(annotation_item.get("completed_by")))
                record_label_association["created_by"] = created_by
                record_label_association["label"] = label
                record_label_association["labeling_task"] = task_name
                record_label_associations[record_item.get("id")].append(
                    record_label_association
                )

        records.append(record)

    return labeling_tasks, records, record_label_associations


def __create_attribute(
    project_id: str, attribute_name: str, attribute_value: Any
) -> None:

    relative_position = attribute.get_relative_position(project_id)
    if relative_position is None:
        relative_position = 1
    else:
        relative_position += 1
    attribute.create(
        project_id,
        attribute_name,
        relative_position,
        __infer_category_enum(attribute_value),
    )


def __infer_category_enum(attribute_value: Any) -> str:
    if isinstance(attribute_value, int):
        return enums.DataTypes.INTEGER.value
    elif isinstance(attribute_value, float):
        return enums.DataTypes.FLOAT.value
    elif isinstance(attribute_value, bool):
        return enums.DataTypes.BOOLEAN.value
    elif isinstance(attribute_value, str):
        return enums.DataTypes.TEXT.value
    else:
        return enums.DataTypes.UNKNOWN.value
