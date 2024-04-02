import json
from fastapi import APIRouter, Request
from controller.auth import manager as auth_manager
from controller.auth.kratos import resolve_user_name_and_email_by_id
from controller.organization import manager
from controller.admin_message import manager as admin_message_manager

from fast_api.routes.client_response import pack_json_result
from submodules.model.util import sql_alchemy_to_dict

router = APIRouter()


ACTIVE_ADMIN_MESSAGES_WHITELIST = {
    "archive_date",
    "created_at",
    "id",
    "level",
    "text",
}


@router.get("")
def get_organization(request: Request):
    user = auth_manager.get_user_by_info(request.state.info)
    organization = manager.get_organization_by_id(user.organization_id)

    return pack_json_result({"data": {"userOrganization": organization}})


@router.get("/overview-stats")
def get_overview_stats(request: Request):
    org_id = str(auth_manager.get_user_by_info(request.state.info).organization_id)
    data = manager.get_overview_stats(org_id)

    return {"data": {"overviewStats": data}}


@router.get("/user-info")
def get_user_info(request: Request):
    user = auth_manager.get_user_by_info(request.state.info)
    data = manager.get_user_info(user)
    return {"data": {"userInfo": data}}


@router.get("/all-users")
def get_all_user(request: Request):
    organization_id = str(
        auth_manager.get_user_by_info(request.state.info).organization.id
    )
    data = manager.get_all_users(organization_id)
    return {"data": {"allUsers": data}}


@router.get("/all-active-admin-messages")
def all_active_admin_messages(request: Request, limit: int = 100) -> str:

    data = admin_message_manager.get_messages(limit, active_only=True)
    data_dict = sql_alchemy_to_dict(
        data, column_whitelist=ACTIVE_ADMIN_MESSAGES_WHITELIST
    )
    return pack_json_result({"data": {"allActiveAdminMessages": data_dict}})


@router.get("/{project_id}/all-users-with-record-count")
def get_all_users_with_record_count(request: Request, project_id: str):
    organization_id = str(
        auth_manager.get_user_by_info(request.state.info).organization.id
    )

    results = manager.get_all_users_with_record_count(organization_id, project_id)

    data = []
    for res in results:
        names, email = resolve_user_name_and_email_by_id(res.user.id)
        last_name = names.get("last", "")
        first_name = names.get("first", "")
        data.append(
            {
                "user": {
                    "id": res.user.id,
                    "mail": email,
                    "firstName": first_name,
                    "lastName": last_name,
                    "__typename": "User",
                },
                "counts": json.dumps(res.counts),
            }
        )

    return pack_json_result({"data": {"allUsersWithRecordCount": data}})


@router.get("/can-create-local-org")
def can_create_local_org(request: Request):
    data = manager.can_create_local()
    return pack_json_result({"data": {"canCreateLocalOrg": data}})
