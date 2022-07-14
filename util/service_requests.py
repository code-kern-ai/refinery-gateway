from typing import Any, Dict

import requests
from graphql import GraphQLError


def post_call_or_raise(url: str, data: Dict[str, Any]) -> Any:
    response = requests.post(url, json=data)
    if response.status_code == 200:
        result, _ = response.json()
        return result
    else:
        raise GraphQLError(response.text)


def get_call_or_raise(url: str, params: Dict = {}) -> Any:
    response = requests.get(url=url, params=params)
    if response.status_code == 200:
        result, _ = response.json()
        return result
    else:
        raise GraphQLError(response.text)


def delete_call_or_raise(url: str) -> int:
    response = requests.delete(url=url)
    if response.status_code == 200:
        return 200
    else:
        raise GraphQLError(response.text)
