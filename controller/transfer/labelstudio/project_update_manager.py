import json
from typing import Dict, Any, List, Tuple

from controller.transfer.labelstudio.util import create_unknown_users
from controller.transfer.record_transfer_manager import download_file
from submodules.model import enums, RecordLabelAssociation
from submodules.model.business_objects import (
    upload_task,
    labeling_task,
    record_label_association,
    general,
    labeling_task_label,
)
from controller.upload_task import manager as upload_task_manager


def manage_data_import(project_id: str, task_id: str) -> None:
    task = upload_task.get(project_id, task_id)
    file_path = download_file(project_id, task)
    mappings = json.loads(task.mappings)
    user_mapping = mappings.get("users")
    user_mapping = create_unknown_users(user_mapping)
    prioritize_existing = mappings.get("prioritizeExisting")
    tasks_by_labels = __get_tasks_by_label_id(project_id)
    label_id_lookup = __get_label_id_lookup(project_id)
    user_ids = __get_user_ids(user_mapping)
    label_ids = __get_projects_label_ids(project_id)

    with open(file_path) as file:
        data = json.load(file)
        association_data = __extract_association_data(
            data, user_mapping, user_ids, label_id_lookup
        )
        record_ids = association_data.keys()
        record_label_associations, remove_list = __check_existing_associations(
            project_id,
            association_data,
            prioritize_existing,
            record_ids,
            user_ids,
            label_ids,
            tasks_by_labels,
        )
        if remove_list:
            record_label_association.delete_by_ids(project_id, remove_list)

        record_label_association.create_by_record_user_label_dict(
            project_id, record_label_associations
        )

    upload_task_manager.update_upload_task_to_finished(task)
    upload_task_manager.update_task(
        project_id, task.id, state=enums.UploadStates.DONE.value, progress=100.0
    )
    general.commit()


def __extract_association_data(
    data: List[Dict[str, Any]],
    user_mapping: Dict[str, str],
    user_ids: List[str],
    label_id_lookup: Dict[str, Any],
) -> Dict[str, Any]:
    record_label_associations = {}
    for record_item in data:
        record_id = record_item.get("data").get("kern_refinery_record_id")
        record_label_associations[record_id] = {user_id: {} for user_id in user_ids}

        for annotation_item in record_item.get("annotations"):
            for result in annotation_item["result"]:
                if (
                    user_mapping.get(str(annotation_item.get("completed_by")))
                    == enums.RecordImportMappingValues.IGNORE.value
                ):
                    continue

                if result.get("type") != "choices":
                    continue

                if len(result.get("value").get("choices")) > 1:
                    continue

                created_by = user_mapping.get(str(annotation_item.get("completed_by")))
                label_name = result.get("value").get("choices")[0]
                task_name = result.get("from_name")
                label_id = label_id_lookup.get(task_name).get(label_name)
                record_label_associations[record_id][created_by][task_name] = str(
                    label_id
                )

    return record_label_associations


def __check_existing_associations(
    project_id: str,
    record_label_associations: Dict[str, Any],
    prioritize_existing: bool,
    record_ids: List[str],
    user_ids: List[str],
    label_ids: List[str],
    tasks_by_labels: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[str]]:
    existing_associations = (
        record_label_association.get_existing_record_label_associations(
            project_id, record_ids, user_ids, label_ids
        )
    )

    remove_list = []
    if prioritize_existing:
        record_label_associations = __extract_incoming_associations_to_hold(
            record_label_associations, existing_associations, tasks_by_labels
        )
    else:
        remove_list = __extract_current_associations_to_remove(
            record_label_associations, existing_associations, tasks_by_labels
        )
    return record_label_associations, remove_list


def __extract_incoming_associations_to_hold(
    record_label_associations: Dict[str, Any],
    existing_associations: List[RecordLabelAssociation],
    tasks_by_labels: Dict[str, Any],
) -> Dict[str, Any]:
    for existing_association in existing_associations:
        task_name = tasks_by_labels.get(
            str(existing_association.labeling_task_label_id)
        )

        record_label_associations.get(str(existing_association.record_id)).get(
            str(existing_association.created_by)
        ).pop(task_name, None)

    return record_label_associations


def __extract_current_associations_to_remove(
    record_label_associations: Dict[str, Any],
    existing_associations: List[RecordLabelAssociation],
    tasks_by_labels: Dict[str, Any],
):
    remove_list = []
    for existing_association in existing_associations:
        task_name = tasks_by_labels.get(
            str(existing_association.labeling_task_label_id)
        )

        if (
            record_label_associations.get(str(existing_association.record_id))
            .get(str(existing_association.created_by))
            .get(task_name)
        ):
            remove_list.append(existing_association.id)
    return remove_list


def __get_user_ids(user_mapping: Dict[str, str]) -> List[str]:
    user_ids = []
    for ls_id, user_id in user_mapping.items():
        if (
            user_id == enums.RecordImportMappingValues.IGNORE
            or user_id == enums.RecordImportMappingValues.UNKNOWN.value
        ):
            continue
        else:
            user_ids.append(user_id)
    return user_ids


def __get_label_id_lookup(project_id: str) -> Dict[str, Any]:
    label_id_lookup = {}
    tasks = labeling_task.get_all(project_id)
    for task in tasks:
        label_id_lookup[task.name] = {}
        for label in task.labels:
            label_id_lookup[task.name][label.name] = label.id
    return label_id_lookup


def __get_projects_label_ids(project_id: str) -> List[str]:
    return [label.id for label in labeling_task_label.get_all(project_id)]


def __get_labels_by_task_name(project_id: str) -> Dict[str, Any]:
    return labeling_task_label.get_labels_by_tasks(project_id)


def __get_tasks_by_label_id(project_id: str) -> Dict[str, Any]:
    return labeling_task.get_labeling_task_name_by_label_id(project_id)
