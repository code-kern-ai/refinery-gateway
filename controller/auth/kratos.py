from email.mime.text import MIMEText
import smtplib
from typing import Union, Any, List, Dict
import os
import requests
import logging
from datetime import datetime, timedelta
from urllib.parse import quote
from controller.user import manager

logging.basicConfig(level=logging.INFO)
logger: logging.Logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

KRATOS_ADMIN_URL = os.getenv("KRATOS_ADMIN_URL")
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = os.getenv("SMTP_PORT")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# user_id -> {"identity" -> full identity, "simple" -> {"id": str, "mail": str, "firstName": str, "lastName": str}}
# "collected" -> timestamp
KRATOS_IDENTITY_CACHE: Dict[str, Any] = {}
KRATOS_IDENTITY_CACHE_TIMEOUT = timedelta(minutes=30)

LANGUAGE_INVITE_WITH_CODE = {
    "en": "Hello!\n\nClick the link to complete your account setup:\n\n{invite_link}\n\nYour one-time code: {recovery_code}\n\n",
    "de": "Hallo!\n\nKlicken Sie auf den Link, um Ihre Kontoeinrichtung abzuschließen:\n\n{invite_link}\n\nIhr Einmal-Code: {recovery_code}\n\n",
}

LANGUAGE_INVITE_CODE_EXPIRATION = {
    "en": "Enter the code on the page. The code is valid for 2 days and can only be used once. Contact your system admin if you have issues.",
    "de": "Geben Sie den Code auf der Seite ein. Der Code ist 2 Tage gültig und kann nur einmal verwendet werden. Kontaktieren Sie Ihren Systemadministrator bei Problemen.",
}

INVITATION_SUBJECT = "Sie sind zu unserer app eingeladen/You are invited to our app"


def get_cached_values(update_db_users: bool = True) -> Dict[str, Dict[str, Any]]:
    global KRATOS_IDENTITY_CACHE
    if not KRATOS_IDENTITY_CACHE or len(KRATOS_IDENTITY_CACHE) == 0:
        __refresh_identity_cache(update_db_users)
    elif (
        KRATOS_IDENTITY_CACHE["collected"] + KRATOS_IDENTITY_CACHE_TIMEOUT
        < datetime.now()
    ):
        __refresh_identity_cache(update_db_users)
    return KRATOS_IDENTITY_CACHE


def __refresh_identity_cache(update_db_users: bool = True) -> None:
    global KRATOS_IDENTITY_CACHE
    request = requests.get(f"{KRATOS_ADMIN_URL}/identities")
    if request.ok:
        collected = datetime.now()
        identities = request.json()

        # maybe more pages https://www.ory.sh/docs/ecosystem/api-design#pagination
        while next_link := __get_link_from_kratos_request(request):
            request = requests.get(next_link)
            if request.ok:
                identities.extend(request.json())

        KRATOS_IDENTITY_CACHE = {
            identity["id"]: {
                "identity": identity,
                "simple": __parse_identity_to_simple(identity),
            }
            for identity in identities
        }

        KRATOS_IDENTITY_CACHE["collected"] = collected
    else:
        KRATOS_IDENTITY_CACHE = {}

    if update_db_users:
        manager.migrate_kratos_users()


def __get_link_from_kratos_request(request: requests.Response) -> str:
    # rel=next only if there is more than 1 page
    # </admin/identities?page_size=1&page_token=00000000-0000-0000-0000-000000000000>; rel="first",</admin/identities?page_size=1&page_token=08f30706-9919-4776-9018-6a56c4fa8bb9>; rel="next"
    link = request.headers.get("Link")
    if link:
        if 'rel="next"' in link:
            parts = link.split("<")
            for part in parts:
                if 'rel="next"' in part:
                    return part.split(">")[0].replace("/admin", KRATOS_ADMIN_URL)
    return None


def __get_identity(user_id: str, only_simple: bool = True) -> Dict[str, Any]:
    if not isinstance(user_id, str):
        user_id = str(user_id)
    cache = get_cached_values()
    if user_id in cache:
        if only_simple:
            return cache[user_id]["simple"]
        return cache[user_id]

    if len(user_id) == 36:
        # check not new entry outside cache
        request = requests.get(f"{KRATOS_ADMIN_URL}/identities/{user_id}")
        if request.ok:
            identity = request.json()
            if identity["id"] == user_id:
                KRATOS_IDENTITY_CACHE[user_id] = {
                    "identity": identity,
                    "simple": __parse_identity_to_simple(identity),
                }
                if only_simple:
                    return KRATOS_IDENTITY_CACHE[user_id]["simple"]
                return KRATOS_IDENTITY_CACHE[user_id]
    # e.g. if id "GOLD_STAR" is requested => wont be in cache but expects a dummy dict
    if only_simple:
        return __parse_identity_to_simple({"id": user_id})
    return {
        "identity": {
            "id": user_id,
            "traits": {"email": None, "name": {"first": None, "last": None}},
        }
    }


def __parse_identity_to_simple(identity: Dict[str, Any]) -> Dict[str, str]:
    r = {
        "id": identity["id"],
        "mail": None,
        "firstName": None,
        "lastName": None,
        "is_admin": get_identity_is_admin(identity),
    }
    if "traits" in identity:
        r["mail"] = identity["traits"]["email"]
        if "name" in identity["traits"]:
            r["firstName"] = identity["traits"]["name"]["first"]
            r["lastName"] = identity["traits"]["name"]["last"]
    return r


def get_userid_from_mail(user_mail: str) -> str:
    values = get_cached_values()
    for key in values:
        if key == "collected":
            continue
        if values[key]["simple"]["mail"] == user_mail:
            return key
    # not in cached values, try search kratos
    return __search_kratos_for_user_mail(user_mail)["id"]


def __search_kratos_for_user_mail(user_mail: str) -> str:
    request = requests.get(
        f"{KRATOS_ADMIN_URL}/identities?preview_credentials_identifier_similar={quote(user_mail)}"
    )
    if request.ok:
        identities = request.json()
        for i in identities:
            if i["traits"]["email"].lower() == user_mail.lower():
                return i
    return None


def resolve_user_mail_by_id(user_id: str) -> str:
    i = __get_identity(user_id)
    if i:
        return i["mail"]
    return None


def resolve_user_name_by_id(user_id: str) -> Dict[str, str]:
    i = __get_identity(user_id, False)
    if i:
        i = i["identity"]
        return i["traits"]["name"] if "name" in i["traits"] else None
    return None


def resolve_all_user_ids(
    relevant_ids: List[str], as_list: bool = True
) -> Union[Dict[str, Dict[str, str]], List[Dict[str, str]]]:
    final = [] if as_list else {}
    for id in relevant_ids:
        i = __get_identity(id)
        if as_list:
            final.append(i)
        else:
            final[id] = i
    return final


def expand_user_mail_name(
    users: List[Dict[str, str]], user_id_key="id"
) -> List[Dict[str, str]]:
    final = []
    for user in users:
        i = __get_identity(user[user_id_key])
        user = {**user, **i}
        final.append(user)
    return final


def resolve_user_name_and_email_by_id(user_id: str) -> dict:
    i = __get_identity(user_id, False)
    if i:
        i = i["identity"]
    if i and "traits" in i and i["traits"]:
        return i["traits"]["name"], i["traits"]["email"]
    return None


def create_user_kratos(email: str, provider: str = None):
    payload_registration = {
        "schema_id": "default",
        "traits": {"email": email},
    }
    if provider:
        payload_registration["metadata_public"] = {
            "registration_scope": {
                "provider_id": provider,
                "invitation_sso": True,
            }
        }
    response_create = requests.post(
        f"{KRATOS_ADMIN_URL}/identities",
        json=payload_registration,
    )
    return response_create.json() if response_create.ok else None


def delete_user_kratos(user_id: str) -> bool:
    response_delete = requests.delete(f"{KRATOS_ADMIN_URL}/identities/{user_id}")
    if response_delete.ok:
        del KRATOS_IDENTITY_CACHE[user_id]
        return True
    return False


def get_recovery_code(user_id: str) -> Dict[str, Any]:
    payload_recovery_code = {
        "expires_in": "48h",
        "identity_id": user_id,
    }
    response = requests.post(
        f"{KRATOS_ADMIN_URL}/recovery/code", json=payload_recovery_code
    )
    if not response.ok:
        logger.warning(
            "Kratos recovery/code failed: status=%s body=%s",
            response.status_code,
            response.text[:500],
        )
    return response.json() if response.ok else None


def send_bulk_invite_emails_with_code(
    emails: List[str], invite_data: List[Dict[str, str]]
) -> None:
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        if SMTP_USER and SMTP_PASSWORD:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)

        for to_email, data in zip(emails, invite_data):
            invite_link = data["invite_link"]
            recovery_code = data["recovery_code"]
            body_de = (
                LANGUAGE_INVITE_WITH_CODE["de"].format(
                    invite_link=invite_link, recovery_code=recovery_code
                )
                + "\n"
                + LANGUAGE_INVITE_CODE_EXPIRATION["de"]
            )
            body_en = (
                LANGUAGE_INVITE_WITH_CODE["en"].format(
                    invite_link=invite_link, recovery_code=recovery_code
                )
                + "\n"
                + LANGUAGE_INVITE_CODE_EXPIRATION["en"]
            )
            msg = MIMEText(f"{body_de}\n\n------\n\n{body_en}")
            msg["Subject"] = INVITATION_SUBJECT
            msg["From"] = "signup@kern.ai"
            msg["To"] = to_email
            server.send_message(msg)


def check_user_exists(email: str) -> bool:
    request = requests.get(
        f"{KRATOS_ADMIN_URL}/identities?preview_credentials_identifier_similar={quote(email)}"
    )
    if request.ok:
        identities = request.json()
        for i in identities:
            if i["traits"]["email"].lower() == email.lower():
                return True
    return False


def get_admin_users_by_public_metadata() -> List[Dict[str, Any]]:
    admins = []
    cache = get_cached_values()
    for key in cache:
        if key == "collected":
            continue
        identity = cache[key]["identity"]
        if (identity.get("metadata_public") or {}).get("role") == "ADMIN" and identity[
            "verifiable_addresses"
        ][0]["verified"]:
            admins.append(cache[key]["simple"])
    return admins


def get_identity_is_admin(identity: Dict[str, Any]) -> bool:

    if (identity.get("metadata_public") or {}).get("role") == "ADMIN" and identity[
        "verifiable_addresses"
    ][0]["verified"]:
        return True
    if (
        identity["traits"]["email"].split("@")[1] == "kern.ai"
        and identity["verifiable_addresses"][0]["verified"]
    ):
        return True
    return False
