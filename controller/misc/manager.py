from controller.misc import config_service


def check_is_managed() -> bool:
    return config_service.get_config_value("is_managed")


def update_config(dict_str: str) -> None:
    return config_service.change_config(dict_str)


def refresh_config() -> None:
    config_service.refresh_config()
