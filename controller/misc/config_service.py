from typing import Dict, Any, Optional, Union
import requests
import time
from submodules.model import daemon
from util import service_requests

__config = None

# these are ment to be constant values since os variables will sooner or later be removed for addresses (and used with values from config-service)
REQUEST_URL = "http://refinery-config:80/full_config"
CHANGE_URL = "http://refinery-config:80/change_config"


def __get_config() -> Dict[str, Any]:
    global __config
    if __config:
        return __config
    refresh_config()
    return __config


def refresh_config():
    response = requests.get(REQUEST_URL)
    if response.status_code != 200:
        raise ValueError(
            f"Config service cant be reached -- response.code{response.status_code}"
        )
    global __config
    __config = response.json()
    daemon.run_without_db_token(invalidate_after, 3600)  # one hour as failsave


def get_config_value(
    key: str, subkey: Optional[str] = None
) -> Union[str, Dict[str, str]]:
    config = __get_config()
    if key not in config:
        raise ValueError(f"Key {key} coudn't be found in config")
    value = config[key]

    if not subkey:
        return value

    if isinstance(value, dict) and subkey in value:
        return value[subkey]
    else:
        raise ValueError(f"Subkey {subkey} coudn't be found in config[{key}]")


def invalidate_after(sec: int) -> None:
    time.sleep(sec)
    global __config
    __config = None


def change_config(dict_str: str) -> None:
    data = {"dict_string": dict_str}
    service_requests.post_call_or_raise(CHANGE_URL, data)
