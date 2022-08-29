import os
from typing import Any, List
from graphql_api.types import ModelProviderInfoResult
from datetime import date

from util import service_requests

BASE_URI = os.getenv("MODEL_PROVIDER")


def get_model_provider_info() -> List[ModelProviderInfoResult]:
    url = f"{BASE_URI}/info"
    return service_requests.get_call_or_raise(url)

def create_model_provider(model_name: str, revision: str) -> Any:
    url =  f"{BASE_URI}/download_model"
    params ={"model_name": str(model_name)}
    if revision:
        params["revision"] = str(revision)
    return service_requests.post_call_or_raise(url, data = None, params = params)


def delete_model_provider(name: str, revision: str) -> Any:
    url = f"{BASE_URI}/delete_model"
    data = {
        "name": str(name),
        "revision": str(revision)
    }
    return service_requests.post_call_or_raise(url,data)