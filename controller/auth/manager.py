import re
from typing import Any, Dict, List, Optional

from controller.auth import kratos
from fastapi import Request
from exceptions.exceptions import (
    AuthManagerError,
    ProjectAccessError,
)
import jwt
from controller.project import manager as project_manager
from controller.user import manager as user_manager
from controller.organization import manager as organization_manager
from submodules.model import enums, exceptions
from submodules.model.business_objects import organization
from submodules.model.business_objects.user import check_email_in_full_admin
from submodules.model.models import Organization, Project, User
import sqlalchemy

DEV_USER_ID = "741df1c2-a531-43b6-b259-df23bc78e9a2"

EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")


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


def check_is_full_admin(request: Any) -> bool:
    if request.url.hostname == "localhost" and request.url.port == 7051:
        return True
    if check_is_admin(request):
        jwt_decoded: Dict[str, Any] = jwt.decode(
            request.headers["Authorization"].split(" ")[1],
            options={"verify_signature": False},
        )
        subject: Dict[str, Any] = jwt_decoded["session"]["identity"]
        if check_email_in_full_admin(subject["traits"]["email"]):
            return True
    return False


def invite_users(
    emails: List[str],
    organization_name: str,
    user_role: str,
    provider: Optional[str] = None,
):
    user_ids = []
    for email in emails:
        # Create accounts for the email
        user = kratos.create_user_kratos(email, provider)
        if not user:
            raise AuthManagerError("User creation failed")
        user_ids.append(user["id"])
        # Assign the account to the organization
        user_manager.update_organization_of_user(organization_name, email)

        # Assign the user role
        user_manager.update_user_role(user["id"], user_role)

        # Get the recovery link for the email
        recovery_link = kratos.get_recovery_link(user["id"])
        if not recovery_link:
            raise AuthManagerError("Failed to get recovery link")

        # Send the recovery link to the email
        kratos.email_with_link(email, recovery_link["recovery_link"])
    return user_ids


def check_valid_emails(emails: List[str]):
    valid_emails = [
        email
        for email in emails
        if is_valid_email(email) and not kratos.check_user_exists(email)
    ]
    all_valid = len(valid_emails) == len(emails)
    return {"valid_emails": valid_emails, "all_valid": all_valid}


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.fullmatch(email))


def check_group_auth(request: Request):
    user_item = get_user_by_info(request.state.info)
    if not user_item:
        raise AuthManagerError(status_code=404, detail="User not found")
    if not user_item.role == enums.UserRoles.ENGINEER.value:
        raise AuthManagerError(status_code=403, detail="User not authorized")
