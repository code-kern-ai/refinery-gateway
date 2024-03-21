from fast_api.routes.client_response import pack_json_result
from fastapi import APIRouter, Request
from submodules.model.business_objects import weak_supervision
from controller.auth import manager as auth_manager
from controller.organization import manager
from submodules.model.util import sql_alchemy_to_dict

router = APIRouter()


@router.get("/weak-supervision-run/{project_id}")
def get_weak_supervision_run(request: Request, project_id: str):
    if project_id:
        auth_manager.check_project_access(request.state.info, project_id)

    user = auth_manager.get_user_by_info(request.state.info)
    data = manager.get_user_info(user)
    ws_data = sql_alchemy_to_dict(
        weak_supervision.get_current_weak_supervision_run(project_id)
    )
    ws_data["user"] = data
    return pack_json_result({"data": {"currentWeakSupervisionRun": ws_data}})
