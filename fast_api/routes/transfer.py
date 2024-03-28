from controller.auth import manager as auth_manager
from controller.transfer import manager as transfer_manager
from fast_api.routes.client_response import pack_json_result
from fastapi import APIRouter, Request


router = APIRouter()


@router.get("/{project_id}/last-record-export-credentials")
def get_last_record_export_credentials(request: Request, project_id: str):
    user_id = auth_manager.get_user_id_by_info(request.state.info)
    data = transfer_manager.last_record_export_credentials(project_id, user_id)
    return pack_json_result({"data": {"lastRecordExportCredentials": data}})
