from typing import Dict, Optional, Any
from submodules.model import User, daemon, enums
from submodules.model.business_objects import user, general
from controller.auth import kratos
from submodules.model.exceptions import EntityNotFoundException
from controller.organization import manager as organization_manager
from datetime import datetime, timedelta
from util.decorator import param_throttle
from submodules.model.util import is_string_true_value


def get_user(user_id: str) -> User:
    user_item = user.get(user_id)
    if user_item:
        update_last_interaction(user_item.id)
    return user_item


def get_or_create_user(user_id: str) -> User:
    user_item = user.get(user_id)
    if not user_item:
        user_item = user.create(user_id, with_commit=True)
        kratos.__refresh_identity_cache()
    update_last_interaction(user_item.id)
    return user_item


def get_or_create_user_by_email(email: str) -> User:
    user_id = kratos.get_userid_from_mail(email)
    return get_or_create_user(user_id)


def get_user_roles() -> Dict[str, str]:
    return {str(u.id): u.role for u in user.get_all()}


def update_organization_of_user(organization_name: str, user_mail: str) -> None:
    organization = organization_manager.get_organization_by_name(organization_name)

    if organization is None:
        raise EntityNotFoundException("Organization not found")

    user_id = kratos.get_userid_from_mail(user_mail)
    if user_id is None:
        raise EntityNotFoundException("User not found")

    user_item = get_or_create_user(user_id)

    if organization.id == user_item.organization:
        raise Exception(
            f"User {user_mail} is already part of organization {organization_name}"
        )
    if user_item.organization:
        raise Exception(
            f"User {user_mail} is already part of organization {user_item.organization.name}"
        )
    user.update_organization(user_item.id, organization.id, with_commit=True)


def update_user_role(user_id: str, role: str) -> User:
    user_item = user.get(user_id)
    if not user_item:
        raise ValueError("User not found")

    try:
        role = enums.UserRoles[role.upper()].value
    except KeyError:
        raise ValueError(f"Invalid role: {role}")
    user_item.role = role
    general.commit()
    return user_item


def update_user_field(user_id: str, field: str, value: Any) -> User:
    user_item = user.get(user_id)
    if not user_item:
        raise ValueError("User not found")
    if field == "use_new_cognition_ui":
        value = is_string_true_value(value)
    setattr(user_item, field, value)
    general.commit()
    return user_item


def remove_organization_from_user(user_mail: str) -> None:
    user_id = kratos.get_userid_from_mail(user_mail)
    if user_id is None:
        raise EntityNotFoundException("User not found")

    user_item = get_or_create_user(user_id)
    if not user_item.organization:
        raise Exception("User has no organization")

    user.remove_organization(user_id, with_commit=True)


def get_active_users_filtered(
    minutes: Optional[int] = None,
    sort_key: Optional[str] = None,
    sort_direction: Optional[str] = None,
    offset: Optional[int] = None,
    limit: Optional[int] = None,
) -> User:
    now = datetime.now()
    last_interaction_range = (now - timedelta(minutes=minutes)) if minutes > 0 else None
    return user.get_active_users_after_filter(
        last_interaction_range, sort_key, sort_direction, offset, limit
    )


@param_throttle(seconds=10)
def update_last_interaction(user_id: str) -> None:
    user.update_last_interaction(user_id)


def delete_user(user_id: str) -> None:
    user.delete(user_id, with_commit=True)
    kratos.__refresh_identity_cache()


def migrate_kratos_users() -> None:
    # this is only supposed to be called during startup of the application
    daemon.run_with_db_token(__migrate_kratos_users)


def __migrate_kratos_users():
    users_kratos = kratos.get_cached_values(False)
    users_database = user.get_all()

    for user_database in users_database:
        user_id = str(user_database.id)
        if user_id not in users_kratos or users_kratos[user_id] is None:
            continue
        user_identity = users_kratos[user_id]["identity"]
        if user_database.email != user_identity["traits"]["email"]:
            user_database.email = user_identity["traits"]["email"]
        if (
            user_database.verified
            != user_identity["verifiable_addresses"][0]["verified"]
        ):
            user_database.verified = user_identity["verifiable_addresses"][0][
                "verified"
            ]
        if (
            user_database.created_at
            != user_identity["verifiable_addresses"][0]["created_at"]
        ):
            user_database.created_at = user_identity["verifiable_addresses"][0][
                "created_at"
            ]
        if user_database.metadata_public != user_identity["metadata_public"]:
            user_database.metadata_public = user_identity["metadata_public"]
        sso_provider = (
            (
                user_identity["metadata_public"]
                .get("registration_scope", {})
                .get("provider_id", None)
            )
            if user_identity["metadata_public"]
            else None
        )
        if user_database.sso_provider != sso_provider:
            user_database.sso_provider = sso_provider

        if user_database.oidc_identifier is None:
            user_search = kratos.__search_kratos_for_user_mail(
                user_identity["traits"]["email"]
            )
            if user_search and user_search["credentials"]:
                if user_search["credentials"].get("oidc", None):
                    oidc = (
                        user_search["credentials"]
                        .get("oidc", {})
                        .get("identifiers", None)[0]
                    )
                    if oidc:
                        oidc = oidc.split(":")
                        if len(oidc) > 1:
                            user_database.oidc_identifier = oidc[1]
                        else:
                            user_database.oidc_identifier = None

    general.commit()
