import os
from datetime import datetime
from typing import Any, List
from fast_api.types import ModelProviderInfoResult

from util import service_requests

BASE_URI = os.getenv("MODEL_PROVIDER")


def get_model_provider_info() -> List[ModelProviderInfoResult]:
    url = f"{BASE_URI}/info"
    model_info = service_requests.get_call_or_raise(url)

    # parse dates to datetime format
    for model in model_info:
        if model["date"]:
            try:
                date = datetime.fromisoformat(model["date"])
                if date:
                    model["date"] = date
            except ValueError:
                pass
            except TypeError:
                pass
        else:
            model["date"] = None

    return model_info


def model_provider_download_model(model_name: str) -> Any:
    url = f"{BASE_URI}/download_model"
    data = {"model_name": model_name}
    return service_requests.post_call_or_raise(url, data=data)


def model_provider_delete_model(name: str) -> Any:
    url = f"{BASE_URI}/delete_model"
    params = {"model_name": name}
    return service_requests.delete_call_or_raise(url, params=params)
