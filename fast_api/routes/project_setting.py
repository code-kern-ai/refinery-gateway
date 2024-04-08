from fast_api.models import (
    CreateNewAttributeBody,
    UpdateAttributeBody,
)
from fastapi import APIRouter, Body, Depends, Request
from typing import Dict

from fastapi.responses import JSONResponse
from controller.task_queue import manager
from controller.auth import manager as auth_manager
from controller.transfer import manager as transfer_manager
from controller.attribute import manager as attribute_manager
from controller.labeling_task_label import manager as label_manager
from controller.labeling_task import manager as task_manager
from controller.project import manager as project_manager
from controller.record import manager as record_manager
from fast_api.routes.client_response import pack_json_result
from submodules.model.enums import TaskType
from submodules.model.util import sql_alchemy_to_dict
from submodules.model import events
from util import doc_ock, notification
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
    data = manager.get_all_waiting_by_type(project_id, task_type)
    data_dict = sql_alchemy_to_dict(data, column_whitelist=QUEUED_TASKS_WHITELIST)
    return pack_json_result({"data": {"queuedTasks": data_dict}})


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
    return pack_json_result({"data": {"attributeByAttributeId": data}})


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
    return pack_json_result({"data": {"checkRenameLabel": data}})


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
    return pack_json_result({"data": {"lastRecordExportCredentials": data}})


@router.post(
    "/{project_id}/prepare-record-export",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
async def prepare_record_export(
    request: Request,
    project_id: str,
):
    try:
        body = await request.json()
        export_options = body.get("options", {}).get("exportOptions")
        export_options = json.loads(export_options)
        key = body.get("options", {}).get("key")
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"message": "Invalid JSON"},
        )

    user_id = auth_manager.get_user_id_by_info(request.state.info)

    try:
        transfer_manager.prepare_record_export(project_id, user_id, export_options, key)
    except Exception as e:
        print(traceback.format_exc(), flush=True)
        return str(e)

    return pack_json_result({"data": {"prepareRecordExport": ""}})


@router.post(
    "/{project_id}/create-label",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
async def create_label(
    request: Request,
    project_id: str,
):
    try:
        body = await request.json()
        label_name = body.get("labelName")
        labeling_task_id = body.get("labelingTaskId")
        label_color = body.get("labelColor")
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"message": "Invalid JSON"},
        )

    if project_id:
        auth_manager.check_project_access(request.state.info, project_id)

    user = auth_manager.get_user_by_info(request.state.info)
    label = label_manager.create_label(
        project_id, label_name, labeling_task_id, label_color
    )
    task = task_manager.get_labeling_task(project_id, labeling_task_id)
    project = project_manager.get_project(project_id)
    doc_ock.post_event(
        str(user.id),
        events.AddLabel(
            ProjectName=f"{project.name}-{project.id}",
            Name=label_name,
            LabelingTaskName=task.name,
        ),
    )
    notification.send_organization_update(
        project_id, f"label_created:{label.id}:labeling_task:{labeling_task_id}"
    )
    return pack_json_result({"data": {"createLabel": ""}})


@router.get(
    "/{project_id}/record-by-record-id",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_record_by_record_id(
    project_id: str,
    record_id: str,
):
    record = record_manager.get_record(project_id, record_id)

    data = {
        "id": str(record.id),
        "data": json.dumps(record.data),
        "projectId": str(record.project_id),
        "category": record.category,
    }

    return pack_json_result({"data": {"recordByRecordId": data}})


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
    return {"data": {"projectSize": final_data}}


@router.post(
    "/{project_id}/create-labels",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
async def create_labels(
    request: Request,
    project_id: str,
):
    try:
        body = await request.json()
        labeling_task_id = body.get("labelingTaskId")
        labels = body.get("labels")
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"message": "Invalid JSON"},
        )

    if project_id:
        auth_manager.check_project_access(request.state.info, project_id)

    user = auth_manager.get_user_by_info(request.state.info)
    created_labels = label_manager.create_labels(project_id, labeling_task_id, labels)
    task = task_manager.get_labeling_task(project_id, labeling_task_id)
    project = project_manager.get_project(project_id)
    for label in created_labels:
        doc_ock.post_event(
            str(user.id),
            events.AddLabel(
                ProjectName=f"{project.name}-{project_id}",
                Name=label.name,
                LabelingTaskName=task.name,
            ),
        )
        notification.send_organization_update(
            project_id, f"label_created:{label.id}:labeling_task:{labeling_task_id}"
        )
    return pack_json_result({"data": {"createLabels": ""}})


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
    return pack_json_result(
        {"data": {"createUserAttribute": {"attributeId": attribute.id}}}
    )


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
    return pack_json_result({"data": {"updateAttribute": {"ok": True}}})


@router.post(
    "/{project_id}/update-project-gates",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def update_project_for_gates(
    request: Request,
    project_id,
):
    user_id = auth_manager.get_user_by_info(request.state.info).id
    project_manager.update_project_for_gates(project_id, user_id)
    return pack_json_result({"data": {"updateProjectGates": {"ok": True}}})
