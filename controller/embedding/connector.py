import os
from typing import Any

from util import service_requests
from . import model_provider_connector

BASE_URI = os.getenv("EMBEDDING_SERVICE")


def request_listing_recommended_encoders() -> Any:
    url = f"{BASE_URI}/classification/recommend/TEXT"  # TODO does here have to be a data type?
    return service_requests.get_call_or_raise(url)


def request_creating_attribute_level_embedding(
    project_id: str, attribute_id: str, user_id: str, config_string: str
) -> Any:
    model_path = model_provider_connector.get_model_path(config_string)

    url = f"{BASE_URI}/classification/encode"
    data = {
        "project_id": str(project_id),
        "attribute_id": str(attribute_id),
        "user_id": str(user_id),
        "config_string": model_path,
    }
    return service_requests.post_call_or_raise(url, data)


def request_creating_token_level_embedding(
    project_id: str, attribute_id: str, user_id: str, config_string: str
) -> Any:
    model_path = model_provider_connector.get_model_path(config_string)

    url = f"{BASE_URI}/extraction/encode"
    data = {
        "project_id": str(project_id),
        "attribute_id": str(attribute_id),
        "user_id": str(user_id),
        "config_string": model_path,
    }
    return service_requests.post_call_or_raise(url, data)


def request_deleting_embedding(project_id: str, embedding_id: str) -> Any:
    url = f"{BASE_URI}/delete/{project_id}/{embedding_id}"
    return service_requests.delete_call_or_raise(url)


def request_tensor_upload(project_id: str, embedding_id: str) -> None:
    url = f"{BASE_URI}/upload_tensor_data/{project_id}/{embedding_id}"
    service_requests.post_call_or_raise(url, {})
