from typing import List
from controller.personal_access_token.util import get_token_and_hash
from submodules.model import enums
from datetime import date
from dateutil.relativedelta import relativedelta

from submodules.model.business_objects import personal_access_token
from submodules.model.models import PersonalAccessToken


def get_personal_access_token(
    project_id: str, user_id: str, name: str
) -> PersonalAccessToken:
    return personal_access_token.get_by_user_and_name(project_id, user_id, name)


def get_all_personal_access_tokens(project_id: str) -> List[PersonalAccessToken]:
    return personal_access_token.get_all(project_id)


def create_personal_access_token(
    project_id: str, user_id: str, name: str, scope: str, expires_at: str
) -> None:
    if personal_access_token.get_by_user_and_name(project_id, user_id, name):
        raise Exception(
            f"Personal Access Key with name {name} already exists for user/project-combination."
        )

    if expires_at == enums.TokenExpireAtValues.ONE_MONTH.value:
        expires_at = date.today() + relativedelta(months=+1)
    elif expires_at == enums.TokenExpireAtValues.THREE_MONTHS.value:
        expires_at = date.today() + relativedelta(months=+3)
    elif expires_at == enums.TokenExpireAtValues.NEVER.value:
        expires_at = None
    else:
        raise Exception(
            f"Option for token expiration date was invalid: Option: {expires_at}."
        )

    if scope not in [enums.TokenScope.READ.value, enums.TokenScope.READ_WRITE.value]:
        raise Exception(f"Option for token scope was invalid: Option: {scope}.")

    token, token_hex_dig = get_token_and_hash()
    personal_access_token.create(
        project_id=project_id,
        created_by=user_id,
        name=name,
        scope=scope,
        expires_at=expires_at,
        token=token_hex_dig,
        with_commit=True,
    )
    return token


def delete_personal_access_token(project_id: str, token_id: str) -> None:
    personal_access_token.delete(project_id, token_id, with_commit=True)
