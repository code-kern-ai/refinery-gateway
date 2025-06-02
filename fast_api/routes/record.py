from typing import Optional
from fastapi import APIRouter, Depends, Request, Body
from controller.record import manager
from controller.auth import manager as auth_manager
from fast_api.routes.client_response import (
    get_custom_response,
    get_silent_success,
)
from fast_api.models import RecordSyncBody, RecordDeletion
from util import notification
from fastapi import status
import json

router = APIRouter()


@router.post(
    "/{project_id}/sync-records",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def sync_records(
    request: Request,
    project_id: str,
    record_sync_body: RecordSyncBody = Body(...),
):
    user_id = auth_manager.get_user_by_info(request.state.info).id
    errors = manager.edit_records(user_id, project_id, record_sync_body.changes)

    if errors and len(errors) > 0:
        return get_custom_response(
            status_code=status.HTTP_200_OK,
            content=json.dumps(errors),
        )

    notification.send_organization_update(project_id, "records_changed")
    return get_silent_success()


@router.delete(
    "/{project_id}/delete-records",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def delete_by_record_ids(
    request: Request,
    project_id: str,
    body: RecordDeletion,
    as_thread: Optional[bool] = False,
):
    # user_id = auth_manager.get_user_by_info(request.state.info).id
    manager.delete_records(project_id, body.record_ids, as_thread)
    return get_silent_success()
