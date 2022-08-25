import os
from typing import Any, List
from graphql_api.types import ModelProviderInfoResult

from util import service_requests

BASE_URI = os.getenv("")


def get_model_provider_info() -> List[ModelProviderInfoResult]:
    # url = f"{BASE_URI}/"
    # return service_requests.get_call_or_raise(url)
    return {
      "name": "Sahajtomar/German_Zeroshot",
      "revision": "d5b0a26665b8538bcb3faa1e63a634cca4c8ee1b",
      "link": "https://huggingface.co/Sahajtomar/German_Zeroshot",
      "date": 1661435904.028773,
      "size": 1343372309
    }

