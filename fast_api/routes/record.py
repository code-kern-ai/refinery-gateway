from fastapi import APIRouter, Depends, Request, Body
from controller.record import manager
from controller.auth import manager as auth_manager
from fast_api.routes.client_response import pack_json_result
from fast_api.models import RecordSyncBody
from util import notification

router = APIRouter()


@router.post("/{project_id}/sync-records")
def sync_records(
    request: Request,
    project_id: str,
    record_sync_body: RecordSyncBody = Body(...),
    access: bool = Depends(auth_manager.check_project_access_dep),
):
    user_id = auth_manager.get_user_by_info(request.state.info).id
    errors = manager.edit_records(user_id, project_id, record_sync_body.changes)

    if errors and len(errors) > 0:
        return pack_json_result(
            {"data": {"editRecords": {"ok": False, "errors": errors}}}
        )

    notification.send_organization_update(project_id, "records_changed")
    return pack_json_result({"data": {"editRecords": {"ok": True}}})
