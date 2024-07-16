from typing import Any, Dict, List
from controller.misc import config_service
from controller.misc import black_white_demo
from fast_api.types import ServiceVersionResult
from submodules.model.global_objects import customer_button
from datetime import datetime
import os
from controller.auth import kratos
from submodules.model.util import sql_alchemy_to_dict
from submodules.model import enums


from util import service_requests

BASE_URI_UPDATER = os.getenv("UPDATER")


def check_is_managed() -> bool:
    return config_service.get_config_value("is_managed")


def check_is_demo() -> bool:
    return config_service.get_config_value("is_demo")


def update_config(dict_str: str) -> None:
    return config_service.change_config(dict_str)


def refresh_config() -> None:
    config_service.refresh_config()


def get_black_white_demo() -> Dict[str, List[str]]:
    return black_white_demo.get_black_white_demo()


def get_version_overview() -> List[ServiceVersionResult]:
    updater_version_overview = __updater_version_overview()
    date_format = "%Y-%m-%dT%H:%M:%S.%f"  # 2022-09-06T12:10:39.167397
    return [
        {
            "service": service["name"],
            "installed_version": service["installed_version"],
            "remote_version": service["remote_version"],
            "last_checked": datetime.strptime(service["last_checked"], date_format),
            "remote_has_newer": service["remote_has_newer"],
            "link": service["link"],
        }
        for service in updater_version_overview
    ]


def has_updates() -> List[ServiceVersionResult]:
    return __updater_has_updates()


# function only sets the versions in the database, not the actual update logic
def update_versions_to_newest() -> None:
    return __update_versions_to_newest()


def __updater_version_overview() -> List[Dict[str, Any]]:
    url = f"{BASE_URI_UPDATER}/version_overview"
    return service_requests.get_call_or_raise(url)


def __updater_has_updates() -> bool:
    url = f"{BASE_URI_UPDATER}/has_updates"
    return service_requests.get_call_or_raise(url)


def __updater_update_to_newest() -> None:
    raise ValueError("This endpoint should only be called from the update batch script")


def __update_versions_to_newest() -> None:
    url = f"{BASE_URI_UPDATER}/update_versions_to_newest"
    return service_requests.post_call_or_raise(url, {})


# def get_all_customer_buttons() -> List[Dict[str, str]]:
#     return finalize_customer_buttons(
#         [sql_alchemy_to_dict(button) for button in customer_button.get_all()]
#     )


def get_org_customer_buttons(org_id: str) -> List[Dict[str, str]]:
    return finalize_customer_buttons(
        [
            sql_alchemy_to_dict(button)
            for button in customer_button.get_by_org_id(org_id)
        ]
    )


def finalize_customer_buttons(
    buttons: List[Dict[str, str]], for_wrapped: bool = False
) -> Dict[str, str]:
    key = "createdBy" if for_wrapped else "created_by"
    key_name = "createdByName" if for_wrapped else "created_by_name"
    key_org_name = "organizationName" if for_wrapped else "organization_name"

    user_ids = {str(e[key]) for e in buttons}  # set comprehension
    name_lookup = {u_id: kratos.resolve_user_name_by_id(u_id) for u_id in user_ids}

    for e in buttons:
        e[key_name] = name_lookup[str(e[key])]
        e[key_name] = (
            (e[key_name]["first"] + " " + e[key_name]["last"])
            if e[key_name]
            else "Unknown"
        )
        # name comes from the join with organization
        e[key_org_name] = e["name"]
        del e["name"]
    return buttons


def check_config_for_type(
    type: enums.CustomerButtonType, config: Dict[str, Any], raise_me: bool = True
) -> str:
    if not config:
        return __raise_or_return(raise_me, "Button must have a config")
    if config.get("icon") is None:
        return __raise_or_return(raise_me, "Button must have an icon")
    t = config.get("tooltip")
    if t is not None and len(t) < 10:
        return __raise_or_return(
            raise_me, "Button tooltip should be at least 10 characters long"
        )
    if type == enums.CustomerButtonType.DATA_MAPPER:
        if config.get("url") is None:
            return __raise_or_return(raise_me, "No url provided for data mapper button")

        # maybe add URL check here
        return  # returns None so "no error"
    return __raise_or_return(raise_me, f"Unknown customer button type: {type}")

    # e.g. for DATA_MAPPER
    # {
    #     "url":"<endpoint_url>", # including access key for e.g. external mapper
    #     "icon":"<icon_name>",
    #     "tooltip":"Map results to HDI D&O Excel"
    # }


def __raise_or_return(raise_me: bool, message: str) -> str:
    if raise_me:
        raise Exception(message)
    return message
