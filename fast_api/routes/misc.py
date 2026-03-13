from exceptions.exceptions import AuthManagerError
from fastapi import APIRouter, Body, Request
from fastapi.responses import FileResponse
from fast_api.models import (
    CancelTaskBody,
    CheckInviteUsersBody,
    InviteUsersBody,
    ModelProviderDeleteModelBody,
    ModelProviderDownloadModelBody,
    AdminQueryFilterBody,
    TestWhereConditionRequest,
)
from fast_api.routes.client_response import (
    pack_json_result,
    get_silent_success,
    GENERIC_FAILURE_RESPONSE,
)
from typing import Dict
from controller.auth import manager as auth
from controller.misc import manager
from controller.monitor import manager as controller_manager
from controller.model_provider import manager as model_provider_manager
from controller.task_master import manager as task_master_manager
from submodules.model import enums
from submodules.model.global_objects import (
    admin_queries as admin_queries_db_go,
)
from submodules.model.sql_validator import validate_sql_clause
from submodules.model.enums import AdminQueries
from submodules.model.business_objects import task_queue as task_queue_bo

router = APIRouter()


@router.get("/is-admin")
def get_is_admin(request: Request) -> Dict:
    return pack_json_result(request.state.adm.is_admin)


@router.get("/version-overview")
def get_version_overview(request: Request) -> Dict:
    data = manager.get_version_overview()
    return pack_json_result(data)


@router.get("/has-updates")
def has_updates(request: Request) -> Dict:
    data = manager.has_updates()
    return pack_json_result(data)


@router.delete("/model-provider-delete-model")
def model_provider_delete_model(
    request: Request, body: ModelProviderDeleteModelBody = Body(...)
):
    if not auth.check_is_single_organization():
        auth.check_admin_access(request.state)
    model_provider_manager.model_provider_delete_model(body.model_name)

    return get_silent_success()


@router.post("/model-provider-download-model")
def model_provider_download_model(
    request: Request, body: ModelProviderDownloadModelBody = Body(...)
):
    if not auth.check_is_single_organization():
        auth.check_admin_access(request.state)
    model_provider_manager.model_provider_download_model(body.model_name)

    return get_silent_success()


@router.get("/all-tasks")
def get_all_tasks(request: Request, page: int = 1, limit: int = 100):
    auth.check_admin_access(request.state)
    tasks = controller_manager.monitor_all_tasks(page=page, limit=limit)
    return pack_json_result(tasks)


@router.delete(
    "/delete-from-task-queue-db",
)
def delete_from_task_queue_db(
    request: Request,
    task_id: str,
    org_id: str,
):
    auth.check_admin_access(request.state)
    task_master_manager.delete_task(org_id, task_id)
    return get_silent_success()


@router.post("/cancel-task")
def cancel_task(
    request: Request,
    body: CancelTaskBody = Body(...),
):

    auth.check_admin_access(request.state)
    task_type = body.task_type
    task_info = body.task_info
    task_id = body.task_id

    task_entity = task_queue_bo.get(task_id)
    if not task_entity:
        return GENERIC_FAILURE_RESPONSE
    if task_entity and (
        task_entity.is_active or task_type == enums.TaskType.PARSE_MARKDOWN_FILE.value
    ):
        if task_type == enums.TaskType.ATTRIBUTE_CALCULATION.value:
            controller_manager.cancel_attribute_calculation(task_info)
        elif task_type == enums.TaskType.EMBEDDING.value:
            controller_manager.cancel_embedding(task_info)
        elif task_type == enums.TaskType.INFORMATION_SOURCE.value:
            controller_manager.cancel_information_source_payload(task_info)
        elif task_type == enums.TaskType.TOKENIZATION.value:
            controller_manager.cancel_record_tokenization_task(task_info)
        elif task_type == enums.TaskType.UPLOAD_TASK.value:
            controller_manager.cancel_upload_task(task_info)
        elif task_type == enums.TaskType.WEAK_SUPERVISION.value:
            controller_manager.cancel_weak_supervision(task_info)
        elif task_type == enums.TaskType.RUN_COGNITION_MACRO.value:
            controller_manager.cancel_macro_execution_task(task_info)
        elif task_type == enums.TaskType.PARSE_COGNITION_FILE.value:
            controller_manager.cancel_parse_cognition_file_task(
                task_entity.organization_id, task_info
            )
        elif task_type == enums.TaskType.EXECUTE_INTEGRATION.value:
            controller_manager.cancel_integration_task(task_info)
        elif task_type == enums.TaskType.EXECUTE_ETL.value:
            controller_manager.cancel_etl_task(task_info)
        else:
            raise ValueError(f"{task_type} is no valid task type")

    task_queue_bo.delete_by_task_id(task_id, True)
    return get_silent_success()


@router.post("/cancel-all-running-tasks")
def cancel_all_running_tasks(request: Request):
    auth.check_admin_access(request.state)
    controller_manager.cancel_all_running_tasks()
    return get_silent_success()


@router.post("/pause-task-queue")
def pause_task_queue(request: Request, task_queue_pause: bool):
    auth.check_admin_access(request.state)
    task_queue_pause_response = task_master_manager.pause_task_queue(task_queue_pause)
    task_queue_pause = False
    if task_queue_pause_response.ok:
        try:
            task_queue_pause = task_queue_pause_response.json()["task_queue_pause"]
        except Exception:
            task_queue_pause = False
    return pack_json_result(task_queue_pause)


@router.get("/pause-task-queue")
def get_task_queue_pause(request: Request):
    auth.check_admin_access(request.state)
    task_queue_pause_response = task_master_manager.get_task_queue_pause()
    task_queue_pause = False
    if task_queue_pause_response.ok:
        try:
            task_queue_pause = task_queue_pause_response.json()["task_queue_pause"]
        except Exception:
            task_queue_pause = False
    return pack_json_result(task_queue_pause)


@router.get("/is-full-admin")
def get_is_full_admin(request: Request) -> Dict:
    data = auth.check_is_full_admin(request)
    return pack_json_result(data)


@router.post("/invite-users")
def invite_users(request: Request, body: InviteUsersBody = Body(...)):
    if not auth.check_is_full_admin(request):
        raise AuthManagerError("Full admin access required")
    user_id = auth.get_user_id_by_info(request.state.info)
    data = auth.invite_users(
        user_id,
        body.emails,
        body.organization_name,
        body.user_role,
        body.language,
        body.provider,
        body.team_ids,
    )
    return pack_json_result(data)


@router.post("/check-valid-emails")
def check_valid_emails(request: Request, body: CheckInviteUsersBody = Body(...)):
    if not auth.check_is_full_admin(request):
        raise AuthManagerError("Full admin access required")
    data = auth.check_valid_emails(body.emails)
    return pack_json_result(data)


# post to allow for a body to be sent
@router.post("/admin-query/{query}")
def get_admin_queries(
    request: Request, query: AdminQueries, body: AdminQueryFilterBody = Body(...)
):
    auth.check_admin_access(request.state)
    if not auth.check_is_full_admin(request):
        raise AuthManagerError("Full admin access required")
    data = admin_queries_db_go.get_result_admin_query(query, body.parameters)
    return pack_json_result(data)


@router.post("/admin-query/{query}/download")
def get_admin_query_excel(
    request: Request, query: AdminQueries, body: AdminQueryFilterBody = Body(...)
):
    auth.check_admin_access(request.state)
    if not auth.check_is_full_admin(request):
        raise AuthManagerError("Full admin access required")

    file_path = manager.create_admin_query_excel(query, body.parameters)

    if file_path is None:
        return GENERIC_FAILURE_RESPONSE
    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.post("/test-where-clause")
def test_where_clause(request: Request, data: TestWhereConditionRequest = Body(...)):
    extend_allowed_nodes = set()
    full_clause_check = False
    for key in data.__dict__.keys():
        if data.__dict__[key] is not None:
            full_clause_check = True
            break
    if full_clause_check:
        extend_allowed_nodes = {"select", "where", "group", "order", "ordered"}

    deny_reason = validate_sql_clause(
        select=data.select,
        where=data.where,
        group_by=data.groupBy,
        order_by=data.orderBy,
        include_db_check=True,
        extend_allowed_nodes=extend_allowed_nodes,
    )
    if extend_allowed_nodes and not isinstance(deny_reason, dict):
        # wrapper to force dict structure for single clause validation with extended nodes
        # print(data.__dict__, flush=True)
        deny_reason = {
            node: deny_reason if data.__dict__[node] else None
            for node in data.__dict__.keys()
        }
    isValid = False
    if full_clause_check:
        isValid = all(v is None for v in deny_reason.values())
    else:
        isValid = deny_reason is None
    return pack_json_result(
        {"isValid": isValid, "denyReason": deny_reason}, wrap_for_frontend=False
    )
