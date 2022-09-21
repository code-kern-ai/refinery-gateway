from typing import Dict
from submodules.model import User, enums
from submodules.model.business_objects import user
from submodules.model.business_objects import general
from controller.auth import kratos
from submodules.model.exceptions import EntityNotFoundException
from controller.organization import manager as organization_manager


def get_user(user_id: str) -> User:
    return user.get(user_id)


def get_or_create_user(user_id: str) -> User:
    user_item = user.get(user_id)
    if not user_item:
        user_item = user.create(user_id, with_commit=True)
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


def remove_organization_from_user(user_mail: str) -> None:
    user_id = kratos.get_userid_from_mail(user_mail)
    if user_id is None:
        raise EntityNotFoundException("User not found")

    user_item = get_or_create_user(user_id)
    if not user_item.organization:
        raise Exception("User has no organization")

    user.remove_organization(user_id, with_commit=True)
