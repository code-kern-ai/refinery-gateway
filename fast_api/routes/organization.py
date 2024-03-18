from fastapi import APIRouter, Request
from controller.auth import manager as auth_manager
from controller.organization import manager
from fast_api.routes.fastapi_resolve_info import FastAPIResolveInfo


router = APIRouter()


@router.get("/overview-stats")
async def get_overview_stats(request: Request):
    info = FastAPIResolveInfo(
        context={"request": request},
        field_name="OrganizationQuery",
        parent_type="Query",
    )

    auth_manager.check_demo_access(info)
    org_id = str(auth_manager.get_user_by_info(info).organization_id)
    data = manager.get_overview_stats(org_id)

    return {"data": {"overviewStats": data}}


@router.get("/user-info")
async def get_user_info(request: Request):
    info = FastAPIResolveInfo(
        context={"request": request},
        field_name="OrganizationQuery",
        parent_type="Query",
    )

    auth_manager.check_demo_access(info)
    data = auth_manager.get_user_by_info(info)

    return {"data": {"userInfo": data}}
