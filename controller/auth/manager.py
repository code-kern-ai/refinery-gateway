from typing import Any, Dict, List, Set

from graphene import ResolveInfo
from controller.misc import config_service
from exceptions.exceptions import NotAllowedInDemoError
import jwt
from graphql import GraphQLError
from controller.project import manager as project_manager
from controller.user import manager as user_manager
from controller.organization import manager as organization_manager
from submodules.model import enums, exceptions
from submodules.model.models import Organization, Project, User
from controller.misc import manager as misc_manager
import sqlalchemy

DEV_USER_ID = "59e8dfca-ce56-44df-a8c7-5f05c61da499"


def get_organization_id_by_info(info) -> Organization:
    organization: Organization = get_user_by_info(info).organization
    if not organization:
        raise GraphQLError("User is not associated to an organization")
    return organization


def get_user_by_info(info) -> User:
    request = info.context["request"]
    if request.url.hostname == "localhost" and request.url.port == 7051:
        user_id = DEV_USER_ID
    else:
        user_id: str = get_user_id_by_jwt_token(request)
    return user_manager.get_or_create_user(user_id)


def get_user_by_id(user_id: str) -> User:
    return user_manager.get_or_create_user(user_id)


def get_user_by_email(email: str) -> User:
    return user_manager.get_or_create_user_by_email(email)


def get_user_id_by_info(info) -> str:
    return get_user_by_info(info).id


def get_user_role_by_info(info) -> str:
    return get_user_by_info(info).role


def get_user_role_by_id(user_id: str) -> str:
    return user_manager.get_user(user_id).role


def get_organization_by_user_id(user_id: str) -> Organization:
    organization: Organization = user_manager.get_or_create_user(user_id).organization
    if not organization:
        raise GraphQLError("User is not associated to an organization")
    return organization


def get_user_id_by_jwt_token(request) -> str:
    claims: Dict[str, Any] = jwt.decode(
        request.headers["Authorization"].split(" ")[1],
        options={"verify_signature": False},
    )
    return claims["session"]["identity"]["id"]


def check_project_access(info, project_id: str) -> None:
    organization_id: str = get_organization_id_by_info(info).id
    project: Project = project_manager.get_project_with_orga_id(
        organization_id, project_id
    )
    # TODO move graphql error into graphql layer
    if project is None:
        raise GraphQLError("Project not found")


def check_admin_access(info) -> None:
    if not check_is_admin(info.context["request"]):
        raise GraphQLError("Admin access required")


def check_project_access_from_user_id(
    user_id: str, project_id: str, from_api: bool = False
) -> bool:
    organization_id: str = get_organization_by_user_id(user_id).id
    try:
        project: Project = project_manager.get_project_with_orga_id(
            organization_id, project_id
        )
    except sqlalchemy.exc.DataError:
        raise exceptions.EntityNotFoundException("Project not found")
    if project is None:
        raise exceptions.EntityNotFoundException("Project not found")
    if from_api:
        user = user_manager.get_user(user_id)
        if user.role != enums.UserRoles.ENGINEER.value:
            raise exceptions.AccessDeniedException("Access denied")
    return True


def check_is_admin(request: Any) -> bool:
    if "Authorization" in request.headers:
        jwt_decoded: Dict[str, Any] = jwt.decode(
            request.headers["Authorization"].split(" ")[1],
            options={"verify_signature": False},
        )
        subject: Dict[str, Any] = jwt_decoded["session"]["identity"]
        if (
            subject["traits"]["email"].split("@")[1] == "kern.ai"
            and subject["verifiable_addresses"][0]["verified"]
        ):
            return True
    return False


def check_demo_access(info: Any) -> None:
    if not check_is_admin(info.context["request"]) and config_service.get_config_value(
        "is_demo"
    ):
        check_black_white(info)


def check_black_white(info: Any):
    black_white = misc_manager.get_black_white_demo()
    if str(info.parent_type) == "Mutation":
        if info.field_name not in black_white["mutations"]:
            raise NotAllowedInDemoError
    elif str(info.parent_type) == "Query":
        if info.field_name in black_white["queries"]:
            raise NotAllowedInDemoError


def check_is_demo_without_info() -> None:
    if config_service.get_config_value("is_demo"):
        raise NotAllowedInDemoError


def check_is_single_organization() -> bool:
    return len(organization_manager.get_all_organizations()) == 1
