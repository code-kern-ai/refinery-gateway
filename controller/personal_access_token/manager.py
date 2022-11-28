import hashlib
from typing import List
from submodules.model import enums
from datetime import date
import secrets
from dateutil.relativedelta import relativedelta

from submodules.model.business_objects import personal_access_token
from submodules.model.models import PersonalAccessToken


def get_personal_access_token(
    project_id: str, user_id: str, name: str
) -> PersonalAccessToken:
    return personal_access_token.get(project_id, user_id, name)


def get_all_personal_access_tokens(
    project_id: str, user_id: str
) -> List[PersonalAccessToken]:
    return personal_access_token.get_all(project_id, user_id)


def create_personal_access_token(
    project_id: str, user_id: str, name: str, scope: str, expires_at: str
) -> None:
    if personal_access_token.get(project_id, user_id, name):
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

    token = secrets.token_urlsafe(80)
    encoded_token = str.encode(token)
    hash_token = hashlib.sha256(encoded_token)
    token_hex_dig = hash_token.hexdigest()

    personal_access_token.create(
        project_id=project_id,
        user_id=user_id,
        name=name,
        scope=scope,
        expires_at=expires_at,
        token=token_hex_dig,
        with_commit=True,
    )
    return token


def delete_personal_access_token(project_id: str, user_id: str, token_id: str) -> None:
    personal_access_token.delete(project_id, user_id, token_id, with_commit=True)
