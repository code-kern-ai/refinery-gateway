import os
from typing import Any, List
from graphql_api.types import ModelProviderInfoResult

from util import service_requests

BASE_URI = os.getenv("MODEL_PROVIDER")


def get_model_provider_info() -> List[ModelProviderInfoResult]:
    url = f"{BASE_URI}/info"
    return service_requests.get_call_or_raise(url)


def model_provider_download_model(
    project_id: str, model_name: str, revision: str
) -> Any:
    url = f"{BASE_URI}/download_model"
    data = {"project_id": project_id, "model_name": model_name, "revision": revision}
    return service_requests.post_call_or_raise(url, data=data)


def model_provider_delete_model(name: str, revision: str) -> Any:
    url = f"{BASE_URI}/delete_model"
    params = {"model_name": name, "revision": revision}
    return service_requests.delete_call_or_raise(url, params=params)
