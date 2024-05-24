from typing import Any, Dict
import requests
from exceptions.exceptions import ServiceRequestsError


def post_call_or_raise(url: str, data: Dict[str, Any]) -> Any:
    response = requests.post(url, json=data)

    if response.status_code != 200:
        raise ServiceRequestsError(response.text)

    if response.headers.get("content-type") == "application/json":
        return response.json()
    else:
        return response.text


def get_call_or_raise(url: str, params: Dict = None) -> Any:
    if params is None:
        params = {}
    response = requests.get(url=url, params=params)
    if response.status_code != 200:
        raise ServiceRequestsError(response.text)

    if response.headers.get("content-type") == "application/json":
        return response.json()
    else:
        return response.text


def delete_call_or_raise(url: str, params: Dict = None) -> int:
    if params is None:
        params = {}
    response = requests.delete(url=url, params=params)
    if response.status_code == 200:
        return 200
    else:
        raise ServiceRequestsError(response.text)
