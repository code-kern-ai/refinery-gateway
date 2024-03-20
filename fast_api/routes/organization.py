from fastapi import APIRouter, Request
from controller.auth import manager as auth_manager
from controller.organization import manager
from controller.admin_message import manager as admin_message_manager

from fast_api.routes.client_response import pack_json_result
from submodules.model.util import sql_alchemy_to_dict

router = APIRouter()


ACTIVE_ADMIN_MESSAGE_KEYS_TO_BE_KEPT = {
    "archive_date",
    "created_at",
    "id",
    "level",
    "text",
}


@router.get("")
def get_organization(request: Request):
    auth_manager.check_demo_access(request.state.info)
    data = auth_manager.get_user_by_info(request.state.info).organization

    return {"data": {"userOrganization": data}}


@router.get("/overview-stats")
def get_overview_stats(request: Request):
    org_id = str(auth_manager.get_user_by_info(request.state.info).organization_id)
    data = manager.get_overview_stats(org_id)

    return {"data": {"overviewStats": data}}


@router.get("/user-info")
def get_user_info(request: Request):
    data = auth_manager.get_user_by_info(request.state.info)

    return {"data": {"userInfo": data}}


@router.get("/all-active-admin-messages")
def all_active_admin_messages(request: Request, limit: int = 100) -> str:
    auth_manager.check_demo_access(request.state.info)
    return pack_json_result(
        {
            "data": {
                "allActiveAdminMessages": [
                    {
                        k: v
                        for k, v in sql_alchemy_to_dict(ds).items()
                        if k in ACTIVE_ADMIN_MESSAGE_KEYS_TO_BE_KEPT
                    }
                    for ds in admin_message_manager.get_messages(
                        limit, active_only=True
                    )
                ]
            }
        },
    )
