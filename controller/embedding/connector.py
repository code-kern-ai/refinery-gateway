import os
from typing import Any, Dict, Union, List

from util import service_requests
import requests

BASE_URI = os.getenv("EMBEDDING_SERVICE")
NEURAL_SEARCH_BASE_URI = os.getenv("NEURAL_SEARCH")


def request_listing_recommended_encoders() -> Any:
    url = f"{BASE_URI}/classification/recommend/TEXT"  # TODO does here have to be a data type?
    return service_requests.get_call_or_raise(url)


def request_embedding(project_id: str, embedding_id: str) -> Any:
    url = f"{BASE_URI}/embed"
    data = {
        "project_id": str(project_id),
        "embedding_id": str(embedding_id),
    }
    return service_requests.post_call_or_raise(url, data)


def request_deleting_embedding(project_id: str, embedding_id: str) -> Any:
    url = f"{BASE_URI}/delete/{project_id}/{embedding_id}"
    return service_requests.delete_call_or_raise(url)


def request_tensor_upload(project_id: str, embedding_id: str) -> None:
    url = f"{BASE_URI}/upload_tensor_data/{project_id}/{embedding_id}"
    service_requests.post_call_or_raise(url, {})


def request_re_embed_records(
    project_id: str, changes: Dict[str, List[Dict[str, Union[str, int]]]]
) -> None:
    # example changes structure:
    # {"<embedding_id>":[{"record_id":"<record_id>","attribute_name":"<attribute_name>","sub_key":"<sub_key>"}]}
    # note that sub_key is optional and only for embedding lists relevant
    url = f"{BASE_URI}/re_embed_records/{project_id}"
    service_requests.post_call_or_raise(url, {"changes": changes})


MODEL_PROVIDER_BASE_URI = os.getenv("MODEL_PROVIDER")


def post_embedding_to_neural_search(project_id: str, embedding_id: str) -> None:
    url = f"{NEURAL_SEARCH_BASE_URI}/recreate_collection"
    params = {
        "project_id": project_id,
        "embedding_id": embedding_id,
    }
    requests.post(url, params=params)


def delete_embedding_from_neural_search(embedding_id: str) -> None:
    url = f"{NEURAL_SEARCH_BASE_URI}/delete_collection"
    params = {"embedding_id": embedding_id}
    requests.put(url, params=params)
