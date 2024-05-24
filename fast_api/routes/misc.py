import json
from fastapi import APIRouter, Body, Request
from exceptions.exceptions import ProjectAccessError
from fast_api.models import (
    ModelProviderDeleteModelBody,
    ModelProviderDownloadModelBody,
)
from fast_api.routes.client_response import pack_json_result
from typing import Dict
from controller.auth import manager as auth
from controller.misc import manager
from controller.misc import manager as misc
from controller.monitor import manager as controller_manager
from controller.model_provider import manager as model_provider_manager
from submodules.model import enums
import util.user_activity

router = APIRouter()


@router.get("/is-admin")
def get_is_admin(request: Request) -> Dict:
    data = auth.check_is_admin(request)
    return pack_json_result({"data": {"isAdmin": data}})


@router.get("/is-demo")
def get_is_demo(request: Request) -> Dict:
    is_demo = False
    try:
        auth.check_demo_access(request.state.info)
    except Exception:
        is_demo = True
    return pack_json_result({"data": {"isDemo": is_demo}})


@router.get("/version-overview")
def get_version_overview(request: Request) -> Dict:
    data = manager.get_version_overview()
    return pack_json_result({"data": {"versionOverview": data}})


@router.get("/has-updates")
def has_updates(request: Request) -> Dict:
    data = manager.has_updates()
    return pack_json_result({"data": {"hasUpdates": data}})


@router.delete("/model-provider-delete-model")
def model_provider_delete_model(
    request: Request, body: ModelProviderDeleteModelBody = Body(...)
):
    if misc.check_is_managed():
        if not auth.check_is_single_organization():
            auth.check_admin_access(request.state.info)
    else:
        raise ProjectAccessError("Not allowed in open source version.")
    model_provider_manager.model_provider_delete_model(body.model_name)

    return pack_json_result({"data": {"modelProviderDeleteModel": {"ok": True}}})


@router.post("/model-provider-download-model")
def model_provider_download_model(
    request: Request, body: ModelProviderDownloadModelBody = Body(...)
):
    if misc.check_is_managed():
        if not auth.check_is_single_organization():
            auth.check_admin_access(request.state.info)
    else:
        raise ProjectAccessError("Not allowed in open source version.")
    model_provider_manager.model_provider_download_model(body.model_name)

    return pack_json_result({"data": {"modelProviderDownloadModel": {"ok": True}}})


@router.get("/all-tasks")
def get_all_tasks(request: Request, only_running: bool):
    auth.check_admin_access(request.state.info)
    tasks = controller_manager.monitor_all_tasks(only_running=only_running)

    all_tasks = []

    for task in tasks:
        started_at = None
        if task.started_at:
            started_at = task.started_at.isoformat()

        finished_at = None
        if task.finished_at:
            finished_at = task.finished_at.isoformat()

        all_tasks.append(
            {
                "projectId": str(task.project_id),
                "state": task.state,
                "taskType": task.task_type,
                "id": str(task.id),
                "createdBy": task.created_by,
                "organizationName": task.organization_name,
                "projectName": task.project_name,
                "startedAt": started_at,
                "finishedAt": finished_at,
            }
        )

    return pack_json_result({"data": {"allTasks": all_tasks}})


@router.post("/cancel-task")
def cancel_task(request: Request, project_id: str, task_id: str, task_type: str):

    auth.check_admin_access(request.state.info)

    if task_type == enums.TaskType.ATTRIBUTE_CALCULATION.value:
        controller_manager.cancel_attribute_calculation(project_id, task_id)
    elif task_type == enums.TaskType.EMBEDDING.value:
        controller_manager.cancel_embedding(project_id, task_id)
    elif task_type == enums.TaskType.INFORMATION_SOURCE.value:
        controller_manager.cancel_information_source_payload(project_id, task_id)
    elif task_type == enums.TaskType.TOKENIZATION.value:
        controller_manager.cancel_record_tokenization_task(project_id, task_id)
    elif task_type == enums.TaskType.UPLOAD_TASK.value:
        controller_manager.cancel_upload_task(project_id, task_id)
    elif task_type == enums.TaskType.WEAK_SUPERVISION.value:
        controller_manager.cancel_weak_supervision(project_id, task_id)
    else:
        raise ValueError(f"{task_type} is no valid task type")

    return pack_json_result({"data": {"cancelTask": {"ok": True}}})


@router.post("/cancel-all-running-tasks")
def cancel_all_running_tasks(request: Request):
    auth.check_admin_access(request.state.info)
    controller_manager.cancel_all_running_tasks()
    return pack_json_result({"data": {"cancelAllRunningTasks": {"ok": True}}})


@router.get("/all-users-activity")
def get_all_users_activity(request: Request):
    auth.check_admin_access(request.state.info)
    data = util.user_activity.resolve_all_users_activity()

    activity = []

    for user in data:
        user_activity = []
        if "user_activity" in user and user["user_activity"] is not None:
            for activity_item in user["user_activity"]:
                user_activity.append(json.dumps(activity_item))

        activity.append(
            {
                "user": {
                    "id": str(user["user_id"]),
                },
                "userActivity": user_activity,
                "warning": user["warning"],
                "warningText": user["warning_text"],
            }
        )

    return pack_json_result({"data": {"allUsersActivity": activity}})
