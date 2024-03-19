from controller.zero_shot import manager
from fast_api.routes.client_response import pack_json_result
from fast_api.routes.fastapi_resolve_info import FastAPIResolveInfo
from fastapi import APIRouter, Request
from controller.auth import manager as auth_manager

router = APIRouter()


@router.get("/zero-shot-recommendations/{project_id}")
def get_zero_shot_recommendations(request: Request, project_id: str):
    info = FastAPIResolveInfo(
        context={"request": request},
        field_name="ZeroShotQuery",
        parent_type="Query",
    )

    auth_manager.check_demo_access(info)
    if project_id:
        auth_manager.check_project_access(info, project_id)

    data = manager.get_zero_shot_recommendations(project_id)
    return pack_json_result({"data": {"zeroShotRecommendations": data}})
