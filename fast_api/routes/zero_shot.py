from controller.zero_shot import manager
from fast_api.routes.client_response import pack_json_result
from fast_api.routes.fastapi_resolve_info import FastAPIResolveInfo
from fastapi import APIRouter, Request


router = APIRouter()


@router.get("/zero-shot-recommendations/{project_id}")
def get_zero_shot_recommendations(request: Request, project_id: str):

    data = manager.get_zero_shot_recommendations(project_id)
    return pack_json_result({"data": {"zeroShotRecommendations": data}})
