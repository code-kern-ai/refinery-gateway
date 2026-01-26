import json
from fastapi import APIRouter, Request, Body, HTTPException
from fast_api.models import (
    AddUserToOrganizationBody,
    ArchiveAdminMessageBody,
    ChangeOrganizationBody,
    ChangeUserRoleBody,
    CreateAdminMessageBody,
    CreateOrganizationBody,
    CreateUpdateReleaseNotificationBody,
    DeleteOrganizationBody,
    DeleteUserBody,
    MappedSortedPaginatedUsers,
    MissingUsersBody,
    RemoveUserToOrganizationBody,
    UpdateOneDriveFieldRequest,
)
from controller.auth import manager as auth_manager
from controller.auth import kratos
from controller.auth.kratos import (
    resolve_user_mail_by_id,
    resolve_user_name_by_id,
)
from controller.organization import manager
from controller.admin_message import manager as admin_message_manager
from controller.organization import manager as organization_manager
from controller.user import manager as user_manager

from fast_api.routes.client_response import get_silent_success, pack_json_result
from submodules.model.business_objects import organization, release_notification, user
from submodules.model.util import sql_alchemy_to_dict
from util import notification

router = APIRouter()


ACTIVE_ADMIN_MESSAGES_WHITELIST = {
    "archive_date",
    "created_at",
    "id",
    "level",
    "text",
    "scheduled_date",
}

USER_INFO_WHITELIST = {
    "id",
    "organization_id",
    "role",
    "language_display",
    "email",
    "use_new_cognition_ui",
    "auto_logout_minutes",
    "one_drive_path",
}
USER_INFO_RENAME_MAP = {"email": "mail"}
ALL_ORGANIZATIONS_WHITELIST = {
    "id",
    "name",
    "created_at",
    "started_at",
    "is_paying",
    "max_rows",
    "max_cols",
    "max_char_count",
    "log_admin_requests",
    "conversation_lifespan_days",
    "file_lifespan_days",
    "token_limit",
}
RELEASE_NOTIFICATIONS_WHITELIST = {"id", "link", "config"}


# in use refinery-ui (07.01.25)
@router.get("")
def get_organization(request: Request):
    user = auth_manager.get_user_by_info(request.state.info)

    return pack_json_result(manager.get_organization_by_id(user.organization_id))


# in use refinery-ui (07.01.25)
@router.get("/overview-stats")
def get_overview_stats(request: Request):
    org_id = str(auth_manager.get_user_by_info(request.state.info).organization_id)

    return pack_json_result(manager.get_overview_stats(org_id), wrap_for_frontend=False)


# in use refinery-ui (07.01.25)
@router.get("/user-info")
def get_user_info(request: Request):
    user = auth_manager.get_user_by_info(request.state.info)
    return pack_json_result(manager.get_user_info(user), wrap_for_frontend=False)


# in use cognition-ui & admin dashboard (07.01.25)
@router.get("/get-user-info-extended")
def get_user_info_extended(request: Request):
    user = auth_manager.get_user_by_info(request.state.info)
    kratos.__refresh_identity_cache()
    name = resolve_user_name_by_id(user.id)
    user_dict = {
        **sql_alchemy_to_dict(
            user,
            column_whitelist=USER_INFO_WHITELIST,
            column_rename_map=USER_INFO_RENAME_MAP,
        ),
        "first_name": name.get("first") if name else None,
        "last_name": name.get("last") if name else None,
    }

    return pack_json_result(user_dict)


# in use admin dashboard (08.01.25)
@router.get("/org-id-name-map")
def get_org_id_name_map(request: Request):
    auth_manager.check_admin_access(request.state.info)
    return pack_json_result(
        organization.get_org_id_to_name_map(), wrap_for_frontend=False
    )


# in use cognition-ui & refinery-ui (08.01.25)
@router.get("/all-users")
def get_all_user(
    request: Request,
    include_engineers: bool = False,
    include_admins: bool = False,
    limited_teams: bool = False,
    org_id: str = None,
):
    relevant_users = []
    user_is_admin = auth_manager.check_is_admin(request)
    if org_id:
        if not user_is_admin:
            raise HTTPException(status_code=403, detail="Not authorized")
        relevant_users = manager.get_all_users(org_id)
    else:
        user_info = auth_manager.get_user_by_info(request.state.info)
        if not user_info.organization_id:
            return pack_json_result([], wrap_for_frontend=False)
        relevant_users = manager.get_all_users(
            user_info.organization_id, limited_teams=limited_teams, user_id=user_info.id
        )
    if include_admins:
        admin_support_users = user_manager.get_admin_users(expand_mail_name=True)
        relevant_users.extend(admin_support_users)
    if include_engineers:
        engineer_users = user_manager.get_engineer_users(
            org_id=user_info.organization_id, expand_mail_name=True
        )
        relevant_users.extend(engineer_users)
    # Remove duplicates by user id
    unique_users = {str(user["id"]): user for user in relevant_users}.values()
    return pack_json_result(list(unique_users), wrap_for_frontend=False)


# in use cognition-ui & refinery-ui & admin-dashboard (08.01.25)
@router.get("/all-active-admin-messages")
def all_active_admin_messages(request: Request, limit: int = 100) -> str:
    data = admin_message_manager.get_messages(limit, active_only=True)
    data_dict = sql_alchemy_to_dict(
        data, column_whitelist=ACTIVE_ADMIN_MESSAGES_WHITELIST
    )
    return pack_json_result(data_dict)


# in use admin-dashboard (08.01.25)
@router.get("/all-admin-messages")
def all_admin_messages(request: Request, limit: int = 100) -> str:
    auth_manager.check_admin_access(request.state.info)
    data = admin_message_manager.get_messages(limit, active_only=False)
    data_dict = sql_alchemy_to_dict(data)
    return pack_json_result(data_dict)


# in use admin-dashboard (08.01.25)
@router.post("/create-organization")
def create_organization(request: Request, body: CreateOrganizationBody = Body(...)):
    auth_manager.check_admin_access(request.state.info)
    organization_manager.create_organization(body.name)
    return get_silent_success()


# in use admin-dashboard (08.01.25)
@router.post("/add-user-to-organization")
def add_user_to_organization(
    request: Request, body: AddUserToOrganizationBody = Body(...)
):
    auth_manager.check_admin_access(request.state.info)
    user_manager.update_organization_of_user(body.organization_name, body.user_mail)
    return get_silent_success()


# in use admin-dashboard (08.01.25)
@router.post("/remove-user-from-organization")
def remove_user_from_organization(
    request: Request, body: RemoveUserToOrganizationBody = Body(...)
):
    auth_manager.check_admin_access(request.state.info)
    user_manager.remove_organization_from_user(body.user_mail)
    return get_silent_success()


# in use admin-dashboard (08.01.25)
@router.post("/change-organization")
def change_organization(request: Request, body: ChangeOrganizationBody = Body(...)):
    auth_manager.check_admin_access(request.state.info)
    organization_manager.change_organization(body.org_id, json.loads(body.changes))
    return get_silent_success()


# in use admin-dashboard (08.01.25)
@router.get("/user-roles")
def get_user_roles(request: Request):
    auth_manager.check_admin_access(request.state.info)
    data = user_manager.get_user_roles()
    return pack_json_result(data, wrap_for_frontend=False)


# in use admin-dashboard (08.01.25)
@router.post("/change-user-role")
def change_user_role(request: Request, body: ChangeUserRoleBody = Body(...)):
    auth_manager.check_admin_access(request.state.info)
    user_manager.update_user_role(body.user_id, body.role)
    return get_silent_success()


# in use admin-dashboard (08.01.25)
@router.get("/all-organizations")
def get_all_organizations(request: Request):
    auth_manager.check_admin_access(request.state.info)
    organizations = manager.get_all_organizations()
    org_dicts = [
        {
            **sql_alchemy_to_dict(org, column_whitelist=ALL_ORGANIZATIONS_WHITELIST),
            "userCount": manager.get_user_count(org.id),
        }
        for org in organizations
    ]
    return pack_json_result(org_dicts)


# in use admin-dashboard (08.01.25)
@router.delete("/delete-organization")
def delete_organization(request: Request, body: DeleteOrganizationBody = Body(...)):
    auth_manager.check_admin_access(request.state.info)
    organization_manager.delete_organization(body.name)
    return get_silent_success()


# in use admin-dashboard (08.01.25)
@router.post("/create-admin-message")
def create_admin_message(request: Request, body: CreateAdminMessageBody = Body(...)):
    auth_manager.check_admin_access(request.state.info)
    user_id = auth_manager.get_user_id_by_info(request.state.info)
    admin_message_manager.create_admin_message(
        body.text, body.level, body.archive_date, body.scheduled_date, user_id
    )
    notification.send_global_update_for_all_organizations("admin_message")
    return get_silent_success()


# in use admin-dashboard (08.01.25)
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
    return get_silent_success()


# in use cognition-ui (23.06.25)
@router.put("/update-user-field/{field}/{value}")
def set_language_display(request: Request, field: str, value: str):
    user_id = auth_manager.get_user_id_by_info(request.state.info)
    user_manager.update_user_field(user_id, field, value)
    return get_silent_success()


# in use cognition-ui (15.12.25)
@router.post("/update-one-drive-field")
def set_one_drive_field(request: Request, body: UpdateOneDriveFieldRequest = Body(...)):
    user_id = auth_manager.get_user_id_by_info(request.state.info)
    user_manager.update_user_field(user_id, "one_drive_path", body.oneDrivePath)
    return get_silent_success()


# in use admin-dashboard (08.01.25)
@router.post("/mapped-sorted-paginated-users")
def get_mapped_sorted_paginated_users(
    request: Request, body: MappedSortedPaginatedUsers = Body(...)
):
    auth_manager.check_admin_access(request.state.info)
    count_users = user_manager.get_active_users_filtered(body.filter_minutes)
    active_users = user_manager.get_active_users_filtered(
        body.filter_minutes, body.sort_key, body.sort_direction, body.offset, body.limit
    )
    active_users = [
        {
            "id": str(user.id),
            "last_interaction": (
                user.last_interaction.isoformat() if user.last_interaction else None
            ),
            "role": user.role,
            "organization": user.organization_name,
            "email": user.email,
            "verified": user.verified,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "metadata_public": user.metadata_public,
            "sso_provider": user.sso_provider,
            "messages_created_this_month": user.messages_created_this_month,
            "messages_created_today": user.messages_created_today,
        }
        for user in active_users
    ]

    return pack_json_result(
        {
            "mappedSortedPaginatedUsers": active_users,
            "fullCountUsers": len(count_users),
        },
        wrap_for_frontend=False,  # needed because it's used like this on the frontend (kratos values)
    )


# in use admin-dashboard (08.01.25)
@router.delete("/delete-user")
def delete_user(request: Request, body: DeleteUserBody = Body(...)):
    auth_manager.check_admin_access(request.state.info)
    user_manager.delete_user(body.user_id)
    return get_silent_success()


# in use admin-dashboard (08.01.25)
@router.post("/missing-users-interaction-and-message-count")
def get_missing_users_interaction(request: Request, body: MissingUsersBody = Body(...)):
    auth_manager.check_admin_access(request.state.info)
    data = user.get_missing_users(body.user_ids)
    return pack_json_result(data, wrap_for_frontend=False)


# in use admin-dashboard (08.01.25)
@router.get("/user-to-organization")
def get_user_to_organization(request: Request):
    auth_manager.check_admin_access(request.state.info)
    data = user.get_user_to_organization()
    return pack_json_result(data, wrap_for_frontend=False)


# in use admin-dashboard (01.10.25)
@router.get("/all-release-notifications-admin")
def get_all_release_notifications(request: Request):
    auth_manager.check_admin_access(request.state.info)
    data = sql_alchemy_to_dict(release_notification.get_all())
    for item in data:
        item["createdByEmail"] = resolve_user_mail_by_id(item["created_by"])
    return pack_json_result(data)


# in use admin-dashboard (08.10.25)
@router.get("/release-notifications")
def get_release_notifications(request: Request):
    data = sql_alchemy_to_dict(
        release_notification.get_all(),
        column_whitelist=RELEASE_NOTIFICATIONS_WHITELIST,
    )
    return pack_json_result(data)


# in use admin-dashboard (01.10.25)
@router.post("/create-release-notification")
def create_release_notification(
    request: Request, body: CreateUpdateReleaseNotificationBody = Body(...)
):
    auth_manager.check_admin_access(request.state.info)
    user_id = auth_manager.get_user_id_by_info(request.state.info)
    validate_result = manager.validate_json_release_notification(body.config)
    if validate_result["is_valid"]:
        release_notification.create(body.link, body.config, user_id, with_commit=True)
    return pack_json_result(validate_result, wrap_for_frontend=False)


# in use admin-dashboard (02.10.25)
@router.put("/update-release-notification/{notification_id}")
def update_release_notification(
    request: Request,
    notification_id: str,
    body: CreateUpdateReleaseNotificationBody = Body(...),
):
    auth_manager.check_admin_access(request.state.info)
    release_notification.update(
        notification_id, body.link, body.config, with_commit=True
    )
    return get_silent_success()


# in use admin-dashboard (02.10.25)
@router.delete("/delete-release-notification/{notification_id}")
def delete_release_notification(request: Request, notification_id: str):
    auth_manager.check_admin_access(request.state.info)
    release_notification.delete(notification_id, with_commit=True)
    return get_silent_success()
