from typing import Dict, List
from controller.misc import config_service
from controller.misc import black_white_demo

def check_is_managed() -> bool:
    return config_service.get_config_value("is_managed")


def update_config(dict_str: str) -> None:
    return config_service.change_config(dict_str)


def refresh_config() -> None:
    config_service.refresh_config()


def get_black_white_demo() -> Dict[str, List[str]]:
    return black_white_demo.get_black_white_demo()
