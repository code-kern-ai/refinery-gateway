import os
from typing import Any, Dict, Union, List, Optional

from exceptions.exceptions import EmbeddingConnectorError
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


def update_attribute_payloads_for_neural_search(
    project_id: str, embedding_id: str, record_ids: Optional[List[str]] = None
) -> bool:
    url = f"{NEURAL_SEARCH_BASE_URI}/update_attribute_payloads"
    data = {
        "project_id": project_id,
        "embedding_id": embedding_id,
    }
    if record_ids:
        data["record_ids"] = record_ids
    try:
        service_requests.post_call_or_raise(url, data)
        return True
    except EmbeddingConnectorError:
        print("couldn't update attribute payloads for neural search", flush=True)
        return False


def collection_on_qdrant(project_id: str, embedding_id: str) -> bool:
    url = f"{NEURAL_SEARCH_BASE_URI}/collection/exist"
    data = {
        "project_id": project_id,
        "embedding_id": embedding_id,
    }
    return service_requests.get_call_or_raise(url, data)["exists"]


def update_label_payloads_for_neural_search(
    project_id: str, embedding_ids: List[str], record_ids: Optional[List[str]] = None
) -> None:
    url = f"{NEURAL_SEARCH_BASE_URI}/update_label_payloads"
    data = {
        "project_id": project_id,
        "embedding_ids": embedding_ids,
    }
    if record_ids:
        data["record_ids"] = record_ids
    service_requests.post_call_or_raise(url, data)


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
