from fast_api.models import (
    CalculateUserAttributeAllRecordsBody,
    CreateNewAttributeBody,
    PrepareProjectExportBody,
    PrepareRecordExportBody,
    UpdateAttributeBody,
)
from fastapi import APIRouter, Body, Depends, Request
from typing import Dict
from controller.auth import manager as auth_manager
from controller.transfer import manager as transfer_manager
from controller.attribute import manager as attribute_manager
from controller.labeling_task_label import manager as label_manager
from controller.project import manager as project_manager
from controller.record import manager as record_manager
from controller.task_master import manager as task_master_manager
from controller.task_queue import manager as task_queue_manager
from fast_api.routes.client_response import (
    pack_json_result,
    get_silent_success,
    GENERIC_FAILURE_RESPONSE,
)
from submodules.model.enums import TaskType
from submodules.model.util import sql_alchemy_to_dict
import traceback
import json


router = APIRouter()

QUEUED_TASKS_WHITELIST = ["id", "project_id", "task_type", "task_id", "task_info"]
ATTRIBUTE_WHITELIST = [
    "id",
    "data_type",
    "is_primary_key",
    "relative_position",
    "user_created",
    "source_code",
    "name",
    "state",
    "logs",
    "visibility",
    "progress",
]


@router.get(
    "/{project_id}/queued-tasks/{task_type}",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_queued_tasks(
    request: Request,
    project_id: str,
    task_type: str,
) -> Dict:
    data = task_queue_manager.get_all_waiting_by_type(project_id, task_type)
    data_dict = sql_alchemy_to_dict(data, column_whitelist=QUEUED_TASKS_WHITELIST)
    return pack_json_result(data_dict)


@router.get(
    "/{project_id}/{attribute_id}/attribute-by-id",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_attribute_by_attribute_id(
    project_id: str,
    attribute_id: str,
):
    data = sql_alchemy_to_dict(
        attribute_manager.get_attribute(project_id, attribute_id),
        column_whitelist=ATTRIBUTE_WHITELIST,
    )
    return pack_json_result(data)


@router.get(
    "/{project_id}/check-rename-label",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def check_rename_label(
    project_id: str,
    label_id: str,
    new_name: str,
):
    data = label_manager.check_rename_label(project_id, label_id, new_name)
    return pack_json_result(data)


@router.get(
    "/{project_id}/last-record-export-credentials",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_last_record_export_credentials(
    request: Request,
    project_id: str,
):
    user_id = auth_manager.get_user_id_by_info(request.state.info)
    data = transfer_manager.last_record_export_credentials(project_id, user_id)
    return pack_json_result(data)


@router.post(
    "/{project_id}/prepare-record-export",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def prepare_record_export(
    request: Request, project_id: str, body: PrepareRecordExportBody
):
    prepared = True
    message = "Export prepared successfully"

    try:
        export_options = json.loads(body.export_options)
        key = body.key
    except json.JSONDecodeError:
        prepared = False
        message = "Invalid JSON"

    user_id = auth_manager.get_user_id_by_info(request.state.info)

    try:
        transfer_manager.prepare_record_export(project_id, user_id, export_options, key)
    except Exception as e:
        print(traceback.format_exc(), flush=True)
        prepared = False
        message = e

    return pack_json_result({"prepared": prepared, "message": message})


@router.get(
    "/{project_id}/record-by-record-id",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_record_by_record_id(
    project_id: str,
    record_id: str,
):
    if record_id is None or record_id == "null":
        return pack_json_result(None)

    record = record_manager.get_record(project_id, record_id)

    data = {
        "id": str(record.id),
        "data": json.dumps(record.data),
        "projectId": str(record.project_id),
        "category": record.category,
    }

    return pack_json_result(data)


@router.get(
    "/{project_id}/project-size",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_project_size(project_id: str):
    data = project_manager.get_project_size(project_id)
    final_data = [
        {
            "byteSize": key.byte_size,
            "byteReadable": key.byte_readable,
            "table": key.table,
            "order": key.order,
            "description": key.description,
            "default": key.default,
        }
        for key in data
    ]
    return pack_json_result(final_data)


@router.post(
    "/{project_id}/create-attribute",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def create_new_attribute(
    request: Request,
    project_id,
    body: CreateNewAttributeBody = Body(...),
):
    attribute = attribute_manager.create_user_attribute(
        project_id, body.name, body.data_type
    )
    return pack_json_result({"attributeId": attribute.id})


@router.post(
    "/{project_id}/update-attribute",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def update_attribute(
    request: Request,
    project_id,
    body: UpdateAttributeBody = Body(...),
):
    attribute_manager.update_attribute(
        project_id,
        body.attribute_id,
        body.data_type,
        body.is_primary_key,
        body.name,
        body.source_code,
        body.visibility,
    )
    return get_silent_success()


@router.post(
    "/{project_id}/calculate-user-attribute-all-records",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def calculate_user_attribute_all_records(
    request: Request,
    project_id: str,
    body: CalculateUserAttributeAllRecordsBody = Body(...),
):
    user = auth_manager.get_user_by_info(request.state.info)
    user_id = user.id
    org_id = user.organization_id
    task_master_manager.queue_task(
        str(org_id),
        str(user_id),
        TaskType.ATTRIBUTE_CALCULATION,
        {
            "project_id": str(project_id),
            "attribute_id": str(body.attribute_id),
        },
        True,
    )

    return get_silent_success()


@router.post(
    "/{project_id}/prepare-project-export",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def prepare_project_export(
    request: Request,
    project_id: str,
    body: PrepareProjectExportBody = Body(...),
):
    user_id = auth_manager.get_user_by_info(request.state.info).id

    try:
        export_options = json.loads(body.export_options)
        transfer_manager.prepare_project_export(
            project_id, user_id, export_options, body.key
        )
    except Exception:
        print(traceback.format_exc(), flush=True)
        return GENERIC_FAILURE_RESPONSE

    return get_silent_success()
