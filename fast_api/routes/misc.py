import json
from fastapi import APIRouter, Body, Request, status
from fastapi.responses import PlainTextResponse
from exceptions.exceptions import ProjectAccessError
from fast_api.models import (
    CancelTaskBody,
    ModelProviderDeleteModelBody,
    ModelProviderDownloadModelBody,
    CreateCustomerButton,
    UpdateCustomerButton,
)
from fast_api.routes.client_response import pack_json_result, SILENT_SUCCESS_RESPONSE
from typing import Dict, Optional
from controller.auth import manager as auth
from controller.misc import manager
from controller.misc import manager as misc
from controller.monitor import manager as controller_manager
from controller.model_provider import manager as model_provider_manager
from controller.task_master import manager as task_master_manager
from submodules.model import enums
from submodules.model.global_objects import customer_button as customer_button_db_go
import util.user_activity
from submodules.model.util import sql_alchemy_to_dict
from submodules.model.enums import (
    try_parse_enum_value,
    CustomerButtonType,
    CustomerButtonLocation,
)

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
def cancel_task(
    request: Request,
    body: CancelTaskBody = Body(...),
):

    auth.check_admin_access(request.state.info)
    task_type = body.task_type
    project_id = body.project_id
    task_id = body.task_id

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


@router.get("/pause-task-queue")
def pause_task_queue(request: Request, task_queue_pause: bool):
    auth.check_admin_access(request.state.info)
    task_master_manager.pause_task_queue(task_queue_pause)
    return SILENT_SUCCESS_RESPONSE


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


# this endpoint is meant to be used by the frontend to get the customer buttons for the current user
# location is a filter to prevent the frontend from having to filter the buttons itself
# also doesn't convert the key!
@router.get("/my-customer-buttons/{location}")
def get_my_customer_buttons(request: Request, location: CustomerButtonLocation):
    # only of users org & filters for visible
    # to be used by everyone, filters for only visible
    org_id = auth.get_user_by_info(request.state.info).organization_id
    if not org_id:
        return pack_json_result([])
    org_id = str(org_id)
    return pack_json_result(
        customer_button_db_go.get_by_org_id(org_id, True, location),
    )


# admin endpoint that converts the keys back to readable format!
@router.get("/all-customer-buttons")
def get_all_customer_buttons(request: Request, only_visible: Optional[bool] = None):
    # all (only for admins on admin page!)
    auth.check_admin_access(request.state.info)

    return pack_json_result(
        manager.finalize_customer_buttons(
            [
                sql_alchemy_to_dict(obj)
                for obj in customer_button_db_go.get_all(only_visible)
            ],
            False,
            True,
        )
    )


@router.post("/create-customer-button")
def add_customer_button(creation_request: CreateCustomerButton, request: Request):
    # all (only for admins on admin page!)
    auth.check_admin_access(request.state.info)
    manager.convert_config_url_key_with_base64(creation_request.config)
    if msg := manager.check_config_for_type(
        creation_request.type, creation_request.config, False
    ):
        return PlainTextResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=msg,
        )
    user_id = auth.get_user_id_by_jwt_token(request)

    return pack_json_result(
        customer_button_db_go.create(
            creation_request.org_id,
            creation_request.type,
            creation_request.location,
            creation_request.config,
            user_id,
            creation_request.visible,
        )
    )


@router.delete("/customer-button/{button_id}")
def delete_customer_buttons(button_id: str, request: Request):
    # all (only for admins on admin page!)
    auth.check_admin_access(request.state.info)
    customer_button_db_go.delete(button_id)
    return SILENT_SUCCESS_RESPONSE


@router.post("/update-customer-button/{button_id}")
def update_customer_buttons(
    button_id: str, update_request: UpdateCustomerButton, request: Request
):
    # (only for admins on admin page!)
    auth.check_admin_access(request.state.info)

    button = customer_button_db_go.get(button_id)
    if not button:
        return PlainTextResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content="Button not found",
        )

    check_type = update_request.type or try_parse_enum_value(
        button.type, CustomerButtonType
    )
    if update_request.config:
        manager.convert_config_url_key_with_base64(update_request.config)
    check_config = update_request.config or button.config

    if msg := manager.check_config_for_type(check_type, check_config, False):
        return PlainTextResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=msg,
        )
    return pack_json_result(
        customer_button_db_go.update(
            button_id,
            update_request.org_id,
            update_request.type,
            update_request.location,
            update_request.config,
            None,  # creation user
            update_request.visible,
        )
    )
