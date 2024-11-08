from typing import Dict, Any, Optional, Union
import time
from config_handler import change_json, get_config
from submodules.model import daemon

__config = None


def __get_config() -> Dict[str, Any]:
    global __config
    if __config:
        return __config
    refresh_config()
    return __config


def refresh_config():
    response = get_config(False)
    global __config
    __config = response
    daemon.run_without_db_token(invalidate_after, 3600)  # one hour as fail safe


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
    config_data = {"dict_string": dict_str}
    return change_json(config_data)
