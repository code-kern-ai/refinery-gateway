from fast_api.models import (
    CalculateUserAttributeAllRecordsBody,
    CreateLabelsBody,
    CreateNewAttributeBody,
    CreateTaskAndLabelsBody,
    PrepareProjectExportBody,
    PrepareRecordExportBody,
    UpdateAttributeBody,
)
from fastapi import APIRouter, Body, Depends, Request
from typing import Dict

from fastapi.responses import JSONResponse
from controller.auth import manager as auth_manager
from controller.transfer import manager as transfer_manager
from controller.attribute import manager as attribute_manager
from controller.labeling_task_label import manager as label_manager
from controller.labeling_task import manager as task_manager
from controller.project import manager as project_manager
from controller.record import manager as record_manager
from controller.task_master import manager as task_master_manager
from controller.task_queue import manager as task_queue_manager
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
    data = task_queue_manager.get_all_waiting_by_type(project_id, task_type)
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
def prepare_record_export(
    request: Request, project_id: str, body: PrepareRecordExportBody
):
    try:
        export_options = json.loads(body.export_options)
        key = body.key
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


@router.get(
    "/{project_id}/record-by-record-id",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_record_by_record_id(
    project_id: str,
    record_id: str,
):
    if record_id is None or record_id == "null":
        return pack_json_result({"data": {"recordByRecordId": None}})

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
def create_labels(
    request: Request,
    project_id: str,
    body: CreateLabelsBody = Body(...),
):
    labeling_task_id = body.labelingTaskId
    labels = body.labels

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

    return pack_json_result(
        {"data": {"calculateUserAttributeAllRecords": {"ok": True}}}
    )


@router.post(
    "/{project_id}/create-task-and-labels",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def create_task_and_labels(
    request: Request,
    project_id: str,
    body: CreateTaskAndLabelsBody = Body(...),
):
    user = auth_manager.get_user_by_info(request.state.info)
    project = project_manager.get_project(project_id)

    item = task_manager.create_labeling_task(
        project_id,
        body.labeling_task_name,
        body.labeling_task_type,
        body.labeling_task_target_id,
    )

    if body.labels is not None:
        label_manager.create_labels(project_id, str(item.id), body.labels)

    doc_ock.post_event(
        str(user.id),
        events.AddLabelingTask(
            ProjectName=f"{project.name}-{project.id}",
            Name=body.labeling_task_name,
            Type=body.labeling_task_type,
        ),
    )

    notification.send_organization_update(
        project_id, f"labeling_task_created:{str(item.id)}"
    )

    return pack_json_result(
        {"data": {"createTaskAndLabels": {"ok": True, "taskId": item.id}}}
    )


@router.post(
    "/{project_id}/prepare-project-export",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def prepare_project_export(
    request: Request,
    project_id: str,
    body: PrepareProjectExportBody = Body(...),
):
    ok = True
    user_id = auth_manager.get_user_by_info(request.state.info).id

    try:
        export_options = json.loads(body.export_options)
        transfer_manager.prepare_project_export(
            project_id, user_id, export_options, body.key
        )
    except Exception:
        print(traceback.format_exc(), flush=True)
        ok = False

    return pack_json_result({"data": {"prepareProjectExport": {"ok": ok}}})
