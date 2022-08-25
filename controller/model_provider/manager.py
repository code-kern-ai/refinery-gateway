import os
from typing import List
from graphql_api.types import ModelProviderInfoResult

from util import service_requests

BASE_URI = os.getenv("MODEL_PROVIDER")


def get_model_provider_info() -> List[ModelProviderInfoResult]:
    url = f"{BASE_URI}/info"
    return service_requests.get_call_or_raise(url)
