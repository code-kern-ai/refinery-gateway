from typing import Optional
from fastapi import APIRouter, Body, status
from controller.record import manager as record_manager
from controller.project import manager as project_manager
from fast_api.routes.client_response import (
    get_custom_response,
    get_silent_success
)
from fast_api.models import RecordDeletion
import json

router = APIRouter()


@router.delete("/{project_id}/delete-records")
def delete_by_record_ids(
    project_id: str,
    body: RecordDeletion,
    as_thread: Optional[bool] = False,
):
    record_manager.delete_records(project_id, body.record_ids, as_thread)
    return get_silent_success()


@router.post(
    "/{project_id}/access-management/sharepoint"
)
def sync_access_groups_and_users_sharepoint(
    project_id: str,
    body: dict = Body(...),
):
    record_ids = body.get("record_ids")
    integration_id = body.get("integration_id")
    permissions_user = body.get("permissions_user", {})
    if len(project_id ) != 36:
        return get_custom_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            content="Project id is not valid",
        )
    if not project_manager.get_project(project_id):
        return get_custom_response(
            status_code=status.HTTP_404_NOT_FOUND,
            content=f"Project with id {project_id} not found",
        )
    if not project_manager.is_access_management_activated(project_id):
        project_manager.activate_access_management(project_id)

    errors = record_manager.sync_access_groups_and_users_sharepoint(project_id, integration_id, permissions_user, record_ids)
    if errors and len(errors) > 0:
        return get_custom_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=json.dumps(errors),
        )
    return get_silent_success()