from typing import Dict, Any
import os
import json

__blacklist_base_config = ["is_managed", "is_demo"]
__config = None

BASE_CONFIG_PATH = "base_config.json"
CURRENT_CONFIG_PATH = "/config/current_config.json"

SERVICES_TO_NOTIFY = {
    "EMBEDDER": "http://refinery-embedder:80",
    "UPDATER": "http://refinery-updater:80",
    "TOKENIZER": "http://refinery-tokenizer:80",
}


def __read_and_change_base_config():
    print("reading base config file", flush=True)
    global __config
    f = open(BASE_CONFIG_PATH)
    __config = json.load(f)

    print("transfer os variables", flush=True)
    __config["is_managed"] = os.getenv("IS_MANAGED") == "1"
    __config["is_demo"] = os.getenv("IS_DEMO") == "1"
    __config["tokens"]["INTERCOM"] = os.getenv("INTERCOM", "")
    __config["s3_region"] = os.getenv("S3_REGION", "eu-west-1")

    __save_current_config()


def change_config(changes: Dict[str, Any]) -> bool:
    global __config
    something_changed = False
    for key in changes:
        if key == "KERN_S3_ENDPOINT":
            continue
        if key in __config:
            if isinstance(changes[key], dict):
                for subkey in changes[key]:
                    if subkey in __config[key]:
                        __config[key][subkey] = changes[key][subkey]
                        something_changed = True
            else:
                __config[key] = changes[key]
                something_changed = True
    if something_changed:
        __save_current_config()
    else:
        print("nothing was changed with input", changes, flush=True)
    return something_changed


def __save_current_config() -> None:
    print("saving config file", flush=True)
    with open(CURRENT_CONFIG_PATH, "w") as f:
        json.dump(__config, f, indent=4)


def init_config() -> None:
    if not os.path.exists(CURRENT_CONFIG_PATH):
        __read_and_change_base_config()
    else:
        __load_and_remove_outdated_config_keys()
    # this one is to be set on every start to ensure its up to date
    print("setting s3 endpoint", flush=True)
    __config["KERN_S3_ENDPOINT"] = os.getenv("KERN_S3_ENDPOINT")


def __load_and_remove_outdated_config_keys():
    if not os.path.exists(CURRENT_CONFIG_PATH):
        return

    global __config
    with open(CURRENT_CONFIG_PATH) as f:
        __config = json.load(f)

    with open(BASE_CONFIG_PATH) as f:
        base_config = json.load(f)

    to_remove = [key for key in __config if key not in base_config]

    if len(to_remove) > 0:
        print("removing outdated config keys", to_remove, flush=True)
        for key in to_remove:
            del __config[key]
        __save_current_config()


def get_config(basic: bool = True) -> Dict[str, Any]:
    global __config, __blacklist_base_config
    if not basic:
        return __config

    return {
        key: __config[key] for key in __config if key not in __blacklist_base_config
    }
