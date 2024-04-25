import json
from fastapi import APIRouter, Depends, Request, Body
from controller.misc import config_service
from fast_api.models import (
    AddUserToOrganizationBody,
    ChangeOrganizationBody,
    CreateOrganizationBody,
    UpdateConfigBody,
)
from controller.auth import manager as auth_manager
from controller.auth.kratos import resolve_user_name_and_email_by_id
from controller.organization import manager
from controller.admin_message import manager as admin_message_manager
from controller.organization import manager as organization_manager
from controller.user import manager as user_manager
from controller.misc import manager as misc

from fast_api.routes.client_response import pack_json_result
from submodules.model import events
from submodules.model.business_objects import organization
from submodules.model.business_objects.user import get
from submodules.model.util import sql_alchemy_to_dict
from util import doc_ock, notification

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


@router.get("/get-user-info-extended")
def get_user_info_extended(request: Request):
    user_id = str(auth_manager.get_user_by_info(request.state.info).id)
    user = get(user_id)
    name, mail = resolve_user_name_and_email_by_id(user_id)

    data = {
        "userInfo": {
            "id": user_id,
            "organizationId": {"id": str(user.organization_id)},
            "firstName": name.get("first"),
            "lastName": name.get("last"),
            "mail": mail,
            "role": user.role,
            "languageDisplay": user.language_display,
        }
    }

    return pack_json_result({"data": data})


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


@router.get(
    "/{project_id}/all-users-with-record-count",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_all_users_with_record_count(
    request: Request,
    project_id: str,
):
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


@router.post("/create-organization")
def create_organization(request: Request, body: CreateOrganizationBody = Body(...)):
    if config_service.get_config_value("is_managed"):
        auth_manager.check_admin_access(request.state.info)
    else:
        if not organization_manager.can_create_local():
            auth_manager.check_admin_access(request.state.info)
    organization = organization_manager.create_organization(body.name)
    return {"data": {"createOrganization": {"organization": organization}}}


@router.post("/add-user-to-organization")
def add_user_to_organization(
    request: Request, body: AddUserToOrganizationBody = Body(...)
):
    if config_service.get_config_value("is_managed"):
        auth_manager.check_admin_access(request.state.info)
    else:
        if not organization_manager.can_create_local(False):
            auth_manager.check_admin_access(request.state.info)
    user = auth_manager.get_user_by_email(body.user_mail)
    user_manager.update_organization_of_user(body.organization_name, body.user_mail)
    doc_ock.register_user(user)
    doc_ock.post_event(str(user.id), events.SignUp())
    return pack_json_result({"data": {"addUserToOrganization": {"ok": True}}})


@router.post("/change-organization")
def change_organization(request: Request, body: ChangeOrganizationBody = Body(...)):
    if config_service.get_config_value("is_managed"):
        auth_manager.check_admin_access(request.state.info)
    organization_manager.change_organization(body.org_id, json.loads(body.changes))
    return pack_json_result({"data": {"changeOrganization": {"ok": True}}})


@router.post("/update-config")
def update_config(request: Request, body: UpdateConfigBody = Body(...)):
    if misc.check_is_managed():
        print(
            "config should only be changed for open source/local version to prevent limit issues"
        )
    misc.update_config(body.dict_str)
    misc.refresh_config()
    orgs = organization.get_all()
    if not orgs or len(orgs) != 1:
        print("local version should only have one organization")

    for org in orgs:
        # send to all so all are notified about the change
        notification.send_organization_update(None, "config_updated", True, str(org.id))
    return pack_json_result({"data": {"updateConfig": {"ok": True}}})


@router.get("/user-roles")
def get_user_roles(request: Request):
    auth_manager.check_admin_access(request.state.info)
    data = user_manager.get_user_roles()
    return {"data": {"userRoles": data}}
