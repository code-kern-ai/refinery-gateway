from typing import Dict, List
from controller.misc import config_service
from controller.misc import black_white_demo
from graphql_api.types import ServiceVersionResult
from datetime import date

def check_is_managed() -> bool:
    return config_service.get_config_value("is_managed")


def update_config(dict_str: str) -> None:
    return config_service.change_config(dict_str)


def refresh_config() -> None:
    config_service.refresh_config()


def get_black_white_demo() -> Dict[str, List[str]]:
    return black_white_demo.get_black_white_demo()

def get_version_overview() -> List[ServiceVersionResult]:
    testArray = []
    testDat = ServiceVersionResult(service='test', installed_version='1.0.0', remote_version='1.0.1', last_checked = date.today(), link='https://www.google.com')
    testArray.append(testDat)
    testDat1 = ServiceVersionResult(service='test1', installed_version='1.0.0', remote_version='1.0.0', last_checked = date.today(), link='https://www.google.com')
    testArray.append(testDat1)

    return testArray
