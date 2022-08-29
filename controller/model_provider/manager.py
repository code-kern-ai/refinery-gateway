import os
from typing import Any, List
from graphql_api.types import ModelProviderInfoResult

from util import service_requests

BASE_URI = os.getenv("MODEL_PROVIDER")


def get_model_provider_info() -> List[ModelProviderInfoResult]:
    url = f"{BASE_URI}/info"
    return service_requests.get_call_or_raise(url)


def create_model_provider(model_name: str, revision: str) -> Any:
    url = f"{BASE_URI}/download_model"
    data = {"model_name": model_name, "revision": revision}
    return service_requests.post_call_or_raise(url, data=data)


def delete_model_provider(name: str, revision: str) -> Any:
    url = f"{BASE_URI}/delete_model"
    params = {"model_name": name, "revision": revision}
    return service_requests.delete_call_or_raise(url, params=params)
