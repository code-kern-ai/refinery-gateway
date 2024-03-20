from fastapi import APIRouter, Request
from controller.auth import manager as auth_manager
from controller.organization import manager


router = APIRouter()


@router.get("/overview-stats")
def get_overview_stats(request: Request):
    org_id = str(auth_manager.get_user_by_info(request.state.info).organization_id)
    data = manager.get_overview_stats(org_id)

    return {"data": {"overviewStats": data}}


@router.get("/user-info")
def get_user_info(request: Request):
    data = auth_manager.get_user_by_info(request.state.info)

    return {"data": {"userInfo": data}}
