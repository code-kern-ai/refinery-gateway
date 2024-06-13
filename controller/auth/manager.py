from typing import Any, Dict

from fastapi import Request
from controller.misc import config_service
from exceptions.exceptions import (
    AuthManagerError,
    NotAllowedInDemoError,
    ProjectAccessError,
)
import jwt
from controller.project import manager as project_manager
from controller.user import manager as user_manager
from controller.organization import manager as organization_manager
from submodules.model import enums, exceptions
from submodules.model.business_objects import organization
from submodules.model.models import Organization, Project, User
from controller.misc import manager as misc_manager
import sqlalchemy

DEV_USER_ID = "741df1c2-a531-43b6-b259-df23bc78e9a2"


def get_organization_id_by_info(info) -> Organization:
    user = get_user_by_info(info)
    if not user or not user.organization_id:
        raise AuthManagerError("User is not associated to an organization")
    return str(user.organization_id)


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
        raise AuthManagerError("User is not associated to an organization")
    return organization


def get_user_id_by_jwt_token(request) -> str:
    claims: Dict[str, Any] = jwt.decode(
        request.headers["Authorization"].split(" ")[1],
        options={"verify_signature": False},
    )
    return claims["session"]["identity"]["id"]


def check_project_access_dep(request: Request, project_id: str):
    if len(project_id) == 36:
        check_project_access(request.state.info, project_id)
    else:
        raise ProjectAccessError


def check_project_access(info, project_id: str) -> None:
    organization_id: str = get_organization_id_by_info(info)
    project: Project = project_manager.get_project_with_orga_id(
        organization_id, project_id
    )

    if project is None:
        raise AuthManagerError("Project not found")


def check_admin_access(info) -> None:
    if not check_is_admin(info.context["request"]):
        raise AuthManagerError("Admin access required")


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


def extract_state_info(request: Request, key: str) -> Any:
    if key not in request.state.parsed:
        value = None
        if key == "user_id":
            value = get_user_id_by_jwt_token(request)
        elif key == "organization_id":
            user = get_user_by_info(request.state.info)
            if user and user.organization_id:
                value = str(user.organization_id)
        elif key == "is_admin":
            value = check_is_admin(request)
        elif key == "log_request":
            # lazy and => db access only if admin is true
            if extract_state_info(request, "is_admin"):
                value = organization.log_admin_requests(
                    extract_state_info(request, "organization_id")
                )
        else:
            raise ValueError(f"unknown {key} in extract_state_info")

        request.state.parsed[key] = value
        return value

    return request.state.parsed[key]
