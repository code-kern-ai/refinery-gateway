from typing import Any, List, Dict, Optional, Union
from controller.misc import config_service

from submodules.model import enums
from submodules.model.business_objects import organization, general, user
from submodules.model.exceptions import EntityAlreadyExistsException
from submodules.model.models import Organization, User
from util import notification
from controller.auth import kratos
from submodules.model.util import sql_alchemy_to_dict
from submodules.s3 import controller as s3

USER_INFO_WHITELIST = {"id", "role"}
ORGANIZATION_WHITELIST = {
    "id",
    "name",
    "max_rows",
    "max_cols",
    "max_char_count",
    "gdpr_compliant",
}


def change_organization(org_id: str, changes: Dict[str, Any]) -> None:
    org = organization.get(org_id)
    if not org:
        raise ValueError(f"Organization with id {org_id} does not exist")

    for k in changes:

        if hasattr(org, k):
            __check_notification(org_id, k, changes[k])
            setattr(org, k, changes[k])
        else:
            raise ValueError(f"Organization has no attribute {k}")
    general.commit()


def get_all_organizations() -> List[Organization]:
    return organization.get_all()


def get_organization_by_name(name: str) -> Organization:
    return organization.get_by_name(name)


def get_organization_by_id(org_id: str) -> Organization:
    org = organization.get(org_id)
    org_dict = sql_alchemy_to_dict(org, column_whitelist=ORGANIZATION_WHITELIST)
    return org_dict


def get_user_info(user) -> User:
    user_filtered = sql_alchemy_to_dict(user, column_whitelist=USER_INFO_WHITELIST)
    (user_expanded,) = kratos.expand_user_mail_name([user_filtered])
    return user_expanded


def get_all_users(
    organization_id: str, user_role: Optional[str] = None, as_dict: bool = True
) -> List[User]:
    parsed = None
    if user_role:
        try:
            parsed = enums.UserRoles[user_role.upper()]
        except KeyError:
            raise ValueError(f"Invalid UserRoles: {user_role}")
    all_users = user.get_all(organization_id, parsed)
    if not as_dict:
        return all_users
    all_users_dict = sql_alchemy_to_dict(
        all_users, column_whitelist=USER_INFO_WHITELIST
    )
    all_users_expanded = kratos.expand_user_mail_name(all_users_dict)
    all_users_expanded = [
        user
        for user in all_users_expanded
        if user["firstName"] is not None and user["lastName"] is not None
    ]
    return all_users_expanded


def create_organization(name: str) -> Organization:
    if organization.get_by_name(name):
        raise EntityAlreadyExistsException(
            f"Organization with name {name} already exists"
        )
    organization_item = organization.create(name, with_commit=True)
    s3.create_bucket(str(organization_item.id))
    return organization_item


def delete_organization(name: str) -> None:
    org = organization.get_by_name(name)
    organization.delete(org.id, with_commit=True)


def get_overview_stats(org_id: str) -> List[Dict[str, Union[str, int]]]:
    if org_id is None:
        return []
    return organization.get_organization_overview_stats(org_id)


def can_create_local(org: bool = True) -> bool:
    if config_service.get_config_value("is_managed"):
        return False
    existing_orgs = organization.get_all()
    checkvalue = 0 if org else 1
    if len(existing_orgs) != checkvalue:
        return False
    if user.get_count_assigned() != 0:
        return False
    return True


def __check_notification(org_id: str, key: str, value: Any):
    if key in ["gdpr_compliant"]:
        notification.send_organization_update(
            None, f"gdpr_compliant:{value}", True, org_id
        )
