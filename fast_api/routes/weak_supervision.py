from fastapi import APIRouter, Request, Body
from controller.weak_supervision import manager
from controller.auth import manager as auth_manager
from fast_api.models import InitWeakSuperVisionBody
from fast_api.routes.client_response import pack_json_result

router = APIRouter()


@router.post("/{project_id}")
def init_weak_supervision(
    request: Request, project_id: str, init_body: InitWeakSuperVisionBody = Body(...)
):
    user_id = auth_manager.get_user_id_by_info(request.state.info)
    manager.run_weak_supervision(
        project_id,
        user_id,
        init_body.overwrite_default_precision,
        init_body.overwrite_weak_supervision,
    )

    return pack_json_result(
        {"data": {"initiateWeakSupervisionByProjectId": {"ok": True}}}
    )
