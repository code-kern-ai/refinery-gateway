from typing import Any, Dict

import requests
from graphql import GraphQLError


def post_call_or_raise(url: str, data: Dict[str, Any]) -> Any:
    response = requests.post(url, json=data)

    if response.status_code != 200:
        raise GraphQLError(response.text)

    return response.json()


def get_call_or_raise(url: str, params: Dict = None) -> Any:
    if params is None:
        params = {}
    response = requests.get(url=url, params=params)
    if response.status_code != 200:
        raise GraphQLError(response.text)

    return response.json()


def delete_call_or_raise(url: str, params: Dict = None) -> int:
    if params is None:
        params = {}
    response = requests.delete(url=url, params=params)
    if response.status_code == 200:
        return 200
    else:
        raise GraphQLError(response.text)
