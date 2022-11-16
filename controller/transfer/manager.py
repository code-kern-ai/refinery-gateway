import os
import json
from typing import Any, List, Optional, Dict
import zipfile
from controller.transfer import export_parser
from controller.transfer.knowledge_base_transfer_manager import (
    import_knowledge_base_file,
)
from controller.transfer.project_transfer_manager import (
    import_file_by_task,
    get_project_export_dump,
)
from controller.transfer.record_export_manager import get_records_by_options_query_data
from controller.transfer.record_transfer_manager import import_file
from controller.attribute import manager as attribute_manager
from controller.transfer.labelstudio import (
    template_generator as labelstudio_template_generator,
    project_creation_manager, project_update_manager,
)
from submodules.model import UploadTask, enums
from submodules.model.business_objects.export import build_full_record_sql_export
from submodules.model.business_objects import (
    attribute,
    organization,
    record_label_association,
    data_slice,
    knowledge_base,
    upload_task,
)
from submodules.model.business_objects import general
from controller.upload_task import manager as upload_task_manager
from submodules.s3 import controller as s3
import pandas as pd
from datetime import datetime
from util import notification
from sqlalchemy.sql import text as sql_text


def get_upload_credentials_and_id(
    project_id: str,
    user_id: str,
    file_name: str,
    file_type: str,
    file_import_options: str,
    upload_type: str,
):
    task = upload_task_manager.create_upload_task(
        str(user_id), project_id, file_name, file_type, file_import_options, upload_type
    )
    org_id = organization.get_id_by_project_id(project_id)
    return s3.get_upload_credentials_and_id(org_id, project_id + "/" + str(task.id))


def import_records_from_file(project_id: str, task: UploadTask) -> None:
    import_file(project_id, task)
    __check_and_add_running_id(project_id, str(task.user_id))


def import_records_from_json(
    project_id: str,
    user_id,
    record_data: Dict[str, Any],
    request_uuid: str,
    is_last: bool,
) -> None:
    request_df = pd.DataFrame(record_data)
    file_path = "tmp_" + request_uuid + ".csv_SCALE"
    if not os.path.exists(file_path):
        request_df.to_csv(file_path, index=False)
    else:
        request_df.to_csv(file_path, mode="a", header=False, index=False)

    if is_last:
        organization_id = organization.get_id_by_project_id(project_id)
        upload_task = upload_task_manager.create_upload_task(
            str(user_id),
            str(project_id),
            f"{file_path}",
            "records",
            "",
        )
        upload_path = f"{project_id}/{str(upload_task.id)}/{file_path}"
        s3.upload_object(organization_id, upload_path, file_path)
        os.remove(file_path)


def __check_and_add_running_id(project_id: str, user_id: str):
    attributes = attribute.get_all(project_id)
    add_running_id = True
    for att in attributes:
        if att.data_type == "INTEGER":
            add_running_id = False
            break
    if add_running_id:
        attribute_manager.add_running_id(user_id, project_id, "running_id", False)


def import_project(project_id: str, task: UploadTask) -> None:
    import_file_by_task(project_id, task)
    record_label_association.update_is_valid_manual_label_for_project(project_id)
    data_slice.update_slice_type_manual_for_project(project_id, with_commit=True)


def import_knowledge_base(project_id: str, task: UploadTask) -> None:
    import_knowledge_base_file(project_id, task)


def export_records(
    project_id: str,
    num_samples: Optional[int] = None,
    user_session_id: Optional[str] = None,
) -> str:
    attributes = attribute.get_all_ordered(project_id, True)
    if not attributes:
        print("no attributes in project --> cancel")
        return None

    final_sql = build_full_record_sql_export(project_id, attributes, user_session_id)

    sql_df = pd.read_sql(sql_text(final_sql), con=general.get_bind())
    if num_samples is not None:
        sql_df = sql_df.head(int(num_samples))
    export_as_csv = False
    if export_as_csv:
        return sql_df.to_csv(index=False)
    else:
        return sql_df.to_json(orient="records")


def prepare_record_export(
    project_id: str, user_id: str, export_options: Optional[Dict[str, Any]] = None
) -> None:
    records_by_options_query_data = get_records_by_options_query_data(
        project_id, export_options
    )

    final_query = records_by_options_query_data.get("final_query")
    mapping_dict = records_by_options_query_data.get("mapping_dict")
    extraction_appends = records_by_options_query_data.get("extraction_appends")

    file_path, file_name = export_parser.parse(
        project_id, final_query, mapping_dict, extraction_appends, export_options
    )
    zip_path, file_name = __write_file_to_zip(file_path)
    org_id = organization.get_id_by_project_id(project_id)
    prefixed_path = f"{project_id}/download/{user_id}/record_export_"
    file_name_download = prefixed_path + file_name

    old_export_files = s3.get_bucket_objects(org_id, prefixed_path)
    for old_export_file in old_export_files:
        s3.delete_object(org_id, old_export_file)

    s3.upload_object(org_id, file_name_download, zip_path)
    notification.send_organization_update(project_id, f"record_export:{user_id}")

    if os.path.exists(file_path):
        os.remove(file_path)
    if os.path.exists(zip_path):
        os.remove(zip_path)


def export_project(
    project_id: str, user_id: str, export_options: Dict[str, bool]
) -> str:
    return get_project_export_dump(project_id, user_id, export_options)


def export_knowledge_base(project_id: str, base_id: str) -> str:
    knowledge_base_item = knowledge_base.get(project_id, base_id)
    if not knowledge_base_item:
        print("no lookup lists in project --> cancel")
        return None
    return json.dumps(
        {
            "name": knowledge_base_item.name,
            "description": knowledge_base_item.description,
            "terms": [
                {
                    "value": item.value,
                    "comment": item.comment,
                    "blacklisted": item.blacklisted,
                }
                for item in knowledge_base_item.terms
            ],
        }
    )


def prepare_project_export(
    project_id: str, user_id: str, export_options: Dict[str, bool]
) -> bool:
    org_id = organization.get_id_by_project_id(project_id)
    objects = s3.get_bucket_objects(org_id, project_id + "/download/project_export_")
    for o in objects:
        s3.delete_object(org_id, o)

    data = get_project_export_dump(project_id, user_id, export_options)
    file_name_base = "project_export_" + datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    file_name_local = file_name_base + ".zip"
    file_name_download = project_id + "/download/" + file_name_local
    __write_json_data_to_zip(data, file_name_base)
    s3.upload_object(org_id, file_name_download, file_name_local)
    notification.send_organization_update(project_id, "project_export")

    if os.path.exists(file_name_local):
        os.remove(file_name_local)
    return True


def __write_file_to_zip(file_path: str) -> str:
    base_name = os.path.basename(file_path)
    file_name = base_name + ".zip"
    zip_path = f"{file_path}.zip"
    zipfile.ZipFile(zip_path, mode="w").write(file_path, base_name)
    return zip_path, file_name


def __write_json_data_to_zip(dumped_json: str, base_file_name: str) -> None:
    with zipfile.ZipFile(
        base_file_name + ".zip",
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as zip_file:
        zip_file.writestr(base_file_name + ".json", data=dumped_json)
        zip_file.testzip()


def last_project_export_credentials(project_id: str) -> str:
    return __get_last_export_credentials(project_id, "/download/project_export_")


def last_record_export_credentials(project_id: str, user_id: str) -> str:
    return __get_last_export_credentials(
        project_id, f"/download/{user_id}/record_export_"
    )


def __get_last_export_credentials(project_id: str, path_prefix: str) -> str:
    org_id = organization.get_id_by_project_id(project_id)
    objects = s3.get_bucket_objects(org_id, project_id + path_prefix)
    if not objects:
        return None
    ordered_objects = sorted(
        objects, key=lambda k: objects[k].last_modified, reverse=True
    )
    for o in ordered_objects:
        return s3.get_download_credentials(
            org_id,
            o,
        )


def generate_labelstudio_template(
    project_id: str, labeling_task_ids: List[str], attribute_ids: List[str]
) -> str:
    return labelstudio_template_generator.generate_template(
        project_id, labeling_task_ids, attribute_ids
    )


def import_label_studio_file(project_id, upload_task_id):
    if attribute.get_all(project_id):
        project_update_manager.manage_data_import(project_id, upload_task_id)
    else:
        project_creation_manager.manage_data_import(project_id, upload_task_id)
    upload_task.update(project_id, upload_task_id, state=enums.UploadStates.DONE.value)