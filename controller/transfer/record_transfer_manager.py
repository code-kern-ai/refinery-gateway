import json
import logging
from typing import Dict, Any, Optional, Tuple, List

import pandas as pd

import controller.labeling_task.util
import controller.transfer.util
from controller.labeling_task.util import filter_existing_tasks_and_labels
from submodules.model.business_objects import (
    attribute,
    general,
    labeling_task_label,
    labeling_task,
    organization,
    project,
    record,
    record_label_association,
)
from controller.user import manager as user_manager
from controller.upload_task import manager as upload_task_manager
from controller.tokenization import manager as token_manager
from util import doc_ock
from submodules.s3 import controller as s3
from submodules.model import enums, events, UploadTask, Attribute
from util import category
from util import notification
from controller.transfer.util import convert_to_record_dict

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
import os
from zipfile import ZipFile


def extract_first_zip_file(local_file_name: str) -> Dict[str, Any]:
    zip_file = ZipFile(local_file_name)
    file_name = zip_file.namelist()[0]
    zip_file.extract(file_name, "")
    return file_name


def import_records_and_rlas(
    project_id: str,
    user_id: str,
    data: List,
    upload_task: Optional[UploadTask] = None,
    record_category: str = enums.RecordCategory.SCALE.value,
):
    CHUNK_SIZE = 500
    chunks = [data[x : x + CHUNK_SIZE] for x in range(0, len(data), CHUNK_SIZE)]
    chunks_count = len(chunks)
    for idx, chunk in enumerate(chunks):
        if upload_task is not None:
            logger.debug(
                upload_task_manager.get_upload_task_message(
                    upload_task,
                    additional_information=f"--- START CHUNK #{idx} ---",
                )
            )

        (
            records_data,
            labels_data,
            tasks_data,
        ) = split_record_data_and_label_data(chunk)

        if idx == 0:
            create_attributes_and_get_text_attributes(project_id, records_data)
            primary_keys = attribute.get_primary_keys(project_id)

        import_labeling_tasks_and_labels_pipeline(
            project_id=project_id, tasks_data=tasks_data
        )
        import_records_and_rlas_pipeline(
            user_id=user_id,
            project_id=project_id,
            records_data=records_data,
            labels_data=labels_data,
            category=record_category,
            primary_keys=primary_keys,
        )

        if upload_task is not None:
            progress = ((idx + 1) / chunks_count) * 100
            upload_task_manager.update_task(
                project_id, upload_task.id, progress=progress
            )


def download_file(project_id: str, upload_task: UploadTask) -> str:
    # TODO is copied from import_file and can be refactored because atm its duplicated code
    upload_task_manager.update_task(
        project_id, upload_task.id, state=enums.UploadStates.PENDING.value
    )
    org_id = organization.get_id_by_project_id(project_id)

    file_type = upload_task.file_name.rsplit("_", 1)[0].rsplit(".", 1)[1]
    download_file_name = s3.download_object(
        org_id,
        project_id + "/" + f"{upload_task.id}/{upload_task.file_name}",
        file_type,
    )
    is_zip = file_type == "zip"
    if is_zip:
        tmp_file_name = extract_first_zip_file(download_file_name)
    else:
        tmp_file_name = download_file_name

    if is_zip and os.path.exists(download_file_name):
        os.remove(download_file_name)

    return tmp_file_name


def import_file(project_id: str, upload_task: UploadTask) -> None:
    # load data from s3 and do transfer task/notification management
    file_type = upload_task.file_name.rsplit("_", 1)[0].rsplit(".", 1)[1]
    tmp_file_name = download_file(project_id, upload_task)

    upload_task_manager.update_task(
        project_id, upload_task.id, state=enums.UploadStates.IN_PROGRESS.value
    )
    record_category = category.infer_category(upload_task.file_name)

    data = convert_to_record_dict(
        file_type,
        tmp_file_name,
        upload_task.user_id,
        upload_task.file_import_options,
        project_id,
    )
    number_records = len(data)
    import_records_and_rlas(
        project_id, upload_task.user_id, data, upload_task, record_category
    )

    upload_task_manager.update_upload_task_to_finished(upload_task)

    user = user_manager.get_or_create_user(upload_task.user_id)
    project_item = project.get(project_id)
    doc_ock.post_event(
        user,
        events.UploadRecords(
            ProjectName=f"{project_item.name}-{project_item.id}", Records=number_records
        ),
    )
    general.commit()


##################### LABELING TASK AND LABELS BLOCK #####################
def import_labeling_tasks_and_labels_pipeline(
    project_id: str, tasks_data: Dict[str, Dict[str, Any]]
) -> None:
    labels_by_tasks = labeling_task_label.get_labels_by_tasks(project_id)

    (
        creatable_tasks,
        creatable_labels,
    ) = filter_existing_tasks_and_labels(tasks_data, labels_by_tasks)
    labeling_task.create_multiple(
        project_id=project_id,
        attribute_ids=attribute.get_attribute_ids(project_id),
        tasks_data=creatable_tasks,
    )
    labeling_task_label.create_labels(
        project_id=project_id,
        task_ids=labeling_task.get_task_name_id_dict(project_id),
        labels_data=creatable_labels,
    )


##################### RECORD AND RECORD LABEL ASSOCIATION BLOCK #####################
def import_records_and_rlas_pipeline(
    user_id: str,
    project_id: str,
    records_data: List[Dict[str, Any]],
    labels_data: List[Dict[str, Any]],
    category: str,
    primary_keys: List[Attribute],
):
    if primary_keys:
        records_data, labels_data = update_records_and_labels(
            user_id=user_id,
            project_id=project_id,
            records_data=records_data,
            labels_data=labels_data,
            primary_keys=primary_keys,
            category=category,
        )
    create_records_and_labels(
        user_id=user_id,
        project_id=project_id,
        records_data=records_data,
        labels_data=labels_data,
        category=category,
    )


def update_records_and_labels(
    user_id: str,
    project_id: str,
    records_data: List[Dict[str, Any]],
    labels_data: List[Dict[str, Any]],
    primary_keys: List[Attribute],
    category: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    existing_records_by_key = record.get_existing_records_by_composite_key(
        project_id=project_id,
        records_data=records_data,
        primary_keys=primary_keys,
        category=category,
    )
    if not existing_records_by_key:
        return records_data, labels_data

    (
        remaining_records_data,
        remaining_labels_data,
        updated_records,
        labels_data_of_updated_records,
    ) = record.update_records(
        records_data=records_data,
        labels_data=labels_data,
        existing_records_by_key=existing_records_by_key,
        primary_keys=primary_keys,
    )
    record_label_association.update_record_label_associations(
        user_id=user_id,
        project_id=project_id,
        records=updated_records,
        labels_data=labels_data_of_updated_records,
    )
    token_manager.delete_token_statistics(updated_records)
    token_manager.delete_docbins(project_id, updated_records)
    return remaining_records_data, remaining_labels_data


def create_records_and_labels(
    user_id: str,
    project_id: str,
    records_data: List[Dict[str, Any]],
    labels_data: List[Dict[str, Any]],
    category: str,
):
    df_check = pd.DataFrame(records_data)
    for key in df_check.columns:
        if df_check[key].dtype.name == "datetime64[ns]":
            df_check[key] = df_check[key].astype(str)
    records_data = df_check.to_dict("records")

    created_records = record.create_records(
        project_id=project_id, records_data=records_data, category=category
    )
    record_label_association.create_record_label_associations(
        records=created_records,
        labels_data=labels_data,
        project_id=project_id,
        user_id=user_id,
    )


##################### HELPER BLOCK ####################
def split_record_data_and_label_data(
    data: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    labels_data = []
    records_data = []
    tasks_data = {}
    for data_item in data:
        record_data = {}
        label_data = {}
        for imported_key, item in data_item.items():
            if "__" in imported_key:
                if (
                    item.strip() == ""
                ):  # if a label is only consists of whitespaces or is empty continue
                    continue

                task_name = controller.labeling_task.util.infer_labeling_task_name(
                    imported_key
                )
                label_data[task_name] = item
                tasks_data[task_name] = tasks_data.get(task_name) or {
                    "attribute": controller.transfer.util.infer_attribute(imported_key)
                    or None,
                    "labels": [],
                }
                if item not in tasks_data.get(task_name).get("labels"):
                    tasks_data.get(task_name).get("labels").append(item)
            else:
                record_data[imported_key] = item
        records_data.append(record_data)
        labels_data.append(label_data)

    return records_data, labels_data, tasks_data


def create_attributes_and_get_text_attributes(
    project_id: str, records_data: List[Dict[str, Any]]
) -> List[Attribute]:
    text_attributes = []
    created_something = False
    df_check = pd.DataFrame(records_data)
    for key in df_check.columns:
        if df_check[key].dtype.name == "datetime64[ns]":
            df_check[key] = df_check[key].astype(str)

        if attribute.get_by_name(project_id, key) is None:
            relative_position = attribute.get_relative_position(project_id)
            if relative_position is None:
                relative_position = 1
            else:
                relative_position += 1
            attribute_item = attribute.create(
                project_id,
                key,
                relative_position,
                category.infer_category_enum(df_check, key),
                False,
            )
            created_something = True
            if attribute_item.data_type == enums.DataTypes.TEXT.value:
                text_attributes.append(attribute_item)
    general.flush()
    if created_something:
        notification.send_organization_update(project_id, f"attributes_updated")

    return text_attributes
