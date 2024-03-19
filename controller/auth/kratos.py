from typing import Union, Any, List, Optional, Dict
from requests import Response
import os
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger: logging.Logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

KRATOS_ADMIN_URL = os.getenv("KRATOS_ADMIN_URL")


def get_userid_from_mail(user_mail: str) -> str:
    for identity in requests.get(f"{KRATOS_ADMIN_URL}/identities").json():
        if identity["traits"]["email"] == user_mail:
            return identity["id"]
    return None


def resolve_user_mail_by_id(user_id: str) -> str:
    res: Response = requests.get("{}/identities/{}".format(KRATOS_ADMIN_URL, user_id))
    data: Any = res.json()
    if res.status_code == 200 and data["traits"]:
        return data["traits"]["email"]
    return None


def resolve_user_name_by_id(user_id: str) -> str:
    res: Response = requests.get("{}/identities/{}".format(KRATOS_ADMIN_URL, user_id))
    data: Any = res.json()
    if res.status_code == 200 and data["traits"]:
        return data["traits"]["name"]
    return None


def resolve_all_user_ids(
    relevant_ids: List[str], as_list: bool = True
) -> List[Dict[str, str]]:
    final = [] if as_list else {}
    for id in relevant_ids:
        r = requests.get(f"{KRATOS_ADMIN_URL}/identities/{id}").json()
        d = {
            "id": id,
            "mail": None,
            "firstName": None,
            "lastName": None,
        }
        if "traits" in r:
            traits = r["traits"]
            d["mail"] = traits["email"]
            d["firstName"] = traits["name"]["first"]
            d["lastName"] = traits["name"]["last"]
        if as_list:
            final.append(d)
        else:
            final[id] = d
    return final


def resolve_user_name_and_email_by_id(user_id: str) -> dict:
    res: Response = requests.get("{}/identities/{}".format(KRATOS_ADMIN_URL, user_id))
    data: Any = res.json()
    if res.status_code == 200 and data["traits"]:
        return data["traits"]["name"], data["traits"]["email"]
    return None
