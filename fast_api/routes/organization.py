import json
from fastapi import APIRouter, Depends, Request, Body
from controller.misc import config_service
from fast_api.models import (
    AddUserToOrganizationBody,
    ArchiveAdminMessageBody,
    ChangeOrganizationBody,
    ChangeUserRoleBody,
    CreateAdminMessageBody,
    CreateOrganizationBody,
    DeleteOrganizationBody,
    RemoveUserToOrganizationBody,
    UpdateConfigBody,
    UserLanguageDisplay,
)
from controller.auth import manager as auth_manager
from controller.auth.kratos import (
    resolve_user_mail_by_id,
    resolve_user_name_and_email_by_id,
)
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
            "organizationId": str(user.organization_id),
            "firstName": name.get("first"),
            "lastName": name.get("last"),
            "mail": mail,
            "role": user.role,
            "languageDisplay": user.language_display,
        }
    }

    return pack_json_result({"data": data})


@router.get("/get-user-info-mini")
def get_user_info_mini(request: Request):
    user_id = str(auth_manager.get_user_by_info(request.state.info).id)
    user = get(user_id)
    name, mail = resolve_user_name_and_email_by_id(user_id)

    data = {
        "userInfo": {
            "id": user_id,
            "organization": {"id": str(user.organization_id)},
            "role": user.role,
        }
    }

    return pack_json_result({"data": data})


@router.get("/all-users")
def get_all_user(request: Request):
    organization_id = auth_manager.get_user_by_info(request.state.info).organization_id
    data = manager.get_all_users(organization_id)
    return {"data": {"allUsers": data}}


@router.get("/all-active-admin-messages")
def all_active_admin_messages(request: Request, limit: int = 100) -> str:

    data = admin_message_manager.get_messages(limit, active_only=True)
    data_dict = sql_alchemy_to_dict(
        data, column_whitelist=ACTIVE_ADMIN_MESSAGES_WHITELIST
    )
    return pack_json_result({"data": {"allActiveAdminMessages": data_dict}})


@router.get("/all-admin-messages")
def all_admin_messages(request: Request, limit: int = 100) -> str:

    data = admin_message_manager.get_messages(limit, active_only=False)
    data_dict = sql_alchemy_to_dict(
        data, column_whitelist=ACTIVE_ADMIN_MESSAGES_WHITELIST
    )
    return pack_json_result({"data": {"allAdminMessages": data_dict}})


@router.get(
    "/{project_id}/all-users-with-record-count",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_all_users_with_record_count(
    request: Request,
    project_id: str,
):
    organization_id = auth_manager.get_user_by_info(request.state.info).organization_id

    results = manager.get_all_users_with_record_count(organization_id, project_id)

    data = []
    for res in results:
        names, email = resolve_user_name_and_email_by_id(res["user_id"])
        last_name = names.get("last", "")
        first_name = names.get("first", "")
        data.append(
            {
                "user": {
                    "id": res["user_id"],
                    "mail": email,
                    "firstName": first_name,
                    "lastName": last_name,
                },
                "counts": json.dumps(res["counts"]),
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


@router.post("/remove-user-from-organization")
def remove_user_from_organization(
    request: Request, body: RemoveUserToOrganizationBody = Body(...)
):
    auth_manager.check_admin_access(request.state.info)
    user_manager.remove_organization_from_user(body.user_mail)
    return pack_json_result({"data": {"removeUserFromOrganization": {"ok": True}}})


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


@router.post("/change-user-role")
def change_user_role(request: Request, body: ChangeUserRoleBody = Body(...)):
    auth_manager.check_admin_access(request.state.info)
    user_manager.update_user_role(body.user_id, body.role)
    return {"data": {"changeUserRole": {"ok": True}}}


@router.get("/all-organizations")
def get_all_organizations(request: Request):
    auth_manager.check_admin_access(request.state.info)
    organizations = manager.get_all_organizations()

    edges = []

    for org in organizations:
        edges.append(
            {
                "node": {
                    "id": str(org.id),
                    "name": org.name,
                    "createdAt": (
                        org.created_at.isoformat()
                        if org.created_at is not None
                        else None
                    ),
                    "startedAt": (
                        org.started_at.isoformat()
                        if org.started_at is not None
                        else None
                    ),
                    "isPaying": org.is_paying,
                    "users": {
                        "edges": [
                            {
                                "node": {
                                    "id": str(user.id),
                                    "mail": resolve_user_mail_by_id(user.id),
                                }
                            }
                            for user in org.users
                        ]
                    },
                    "maxRows": org.max_rows,
                    "maxCols": org.max_cols,
                    "maxCharCount": org.max_char_count,
                    "gdprCompliant": org.gdpr_compliant,
                }
            }
        )

    data = {"edges": edges}

    return pack_json_result({"data": {"allOrganizations": data}})


@router.delete("/delete-organization")
def delete_organization(request: Request, body: DeleteOrganizationBody = Body(...)):
    auth_manager.check_admin_access(request.state.info)
    organization_manager.delete_organization(body.name)
    return pack_json_result({"data": {"deleteOrganization": {"ok": True}}})


@router.get("/active-users")
def get_active_users(request: Request):
    auth_manager.check_admin_access(request.state.info)
    activeUsers = user_manager.get_active_users(None, None)

    activeUsers = [
        {
            "id": str(user.id),
            "lastInteraction": (
                user.last_interaction.isoformat() if user.last_interaction else None
            ),
        }
        for user in activeUsers
    ]

    return {"data": {"activeUsers": activeUsers}}


@router.post("/create-admin-message")
def create_admin_message(request: Request, body: CreateAdminMessageBody = Body(...)):
    auth_manager.check_admin_access(request.state.info)
    user_id = auth_manager.get_user_id_by_info(request.state.info)
    admin_message_manager.create_admin_message(
        body.text, body.level, body.archive_date, user_id
    )
    notification.send_global_update_for_all_organizations("admin_message")
    return pack_json_result({"data": {"createAdminMessage": {"ok": True}}})


@router.delete("/archive-admin-message")
def archive_admin_message(
    request: Request,
    body: ArchiveAdminMessageBody = Body(...),
):
    auth_manager.check_admin_access(request.state.info)
    user_id = auth_manager.get_user_id_by_info(request.state.info)
    admin_message_manager.archive_admin_message(
        body.message_id, user_id, body.archived_reason
    )
    notification.send_global_update_for_all_organizations("admin_message")
    return pack_json_result({"data": {"archiveAdminMessage": {"ok": True}}})


@router.post("/set-language-display")
def set_language_display(request: Request, body: UserLanguageDisplay = Body(...)):
    user_manager.update_user_language_display(body.user_id, body.language_display)
    return pack_json_result({"data": {"changeUserLanguageDisplay": {"ok": True}}})
