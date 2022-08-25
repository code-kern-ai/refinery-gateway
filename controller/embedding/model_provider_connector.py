import os
from util import service_requests

BASE_URI = os.getenv("MODEL_PROVIDER")


def get_model_path(config_string: str, revision: str = None) -> str:
    url = f"{BASE_URI}/model_path"
    data = {
        "config_string": config_string,
        "revision": revision,
    }
    return service_requests.get_call_or_raise(url, params=data)
