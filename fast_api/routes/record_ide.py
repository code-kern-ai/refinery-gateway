from fastapi import APIRouter, Depends, Request, Body
from controller.record_ide import manager
from controller.auth import manager as auth_manager
from fast_api.models import RecordIdeBody
from fast_api.routes.client_response import pack_json_result

router = APIRouter()


@router.post(
    "/{project_id}/{record_id}/record-ide",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_record_ide(
    request: Request,
    project_id: str,
    record_id: str,
    record_ide_body: RecordIdeBody = Body(...),
):

    user_id = auth_manager.get_user_by_info(request.state.info).id
    return pack_json_result(
        {
            "data": {
                "runRecordIde": manager.create_record_ide_payload(
                    user_id, project_id, record_id, record_ide_body.code
                )
            }
        }
    )
