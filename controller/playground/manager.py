from fast_api.routes.client_response import pack_json_result, GENERIC_FAILURE_RESPONSE
from typing import List, Any, Optional, Tuple, Dict
import os
import requests

NEURAL_SEARCH = os.getenv("NEURAL_SEARCH")
EMBEDDING_SERVICE = os.getenv("EMBEDDING_SERVICE")

LIMIT = 10
FILTER = None
THRESHOLD = None


def get_search_result_for_text(project_id: str, embedding_id: str, question: str):
    question_tensor = __get_tensors_for_texts(project_id, embedding_id, [question])

    if question_tensor and question_tensor[0]:
        return __get_most_similar_records(
            project_id, embedding_id, question_tensor[0], LIMIT
        )
    else:
        return []


def get_search_result_for_eval_set(
    project_id: str, embedding_id: str, eval_set_id: str
):
    question_tensor = __get_tensors_for_texts(project_id, embedding_id, [question])

    if question_tensor is None:
        return GENERIC_FAILURE_RESPONSE
    elif len(question_tensor) == 0:
        return pack_json_result([])

    search_results = __get_most_similar_records(
        project_id, embedding_id, question_tensor[0], LIMIT
    )
    return search_results


def create_evaluation_set(project_id: str, question: str, record_ids: List[str]):
    pass


def get_evaluation_set_by_id(project_id: str, set_id: str):
    pass


def get_evaluation_sets(project_id: str):
    pass


def create_evaluation_group(project_id: str, name: str, evaluation_set_ids: List[str]):
    pass


def get_evaluation_group_by_id(project_id: str, group_id: str):
    pass


def get_evaluation_groups(project_id: str):
    pass


def __get_tensors_for_texts(
    refinery_project_id: str, embedding_id: str, texts: List[str]
) -> Tuple[bool, Optional[List[Any]]]:

    url = f"{EMBEDDING_SERVICE}/calc-tensor-by-pkl/{refinery_project_id}/{embedding_id}"

    response = requests.post(
        url,
        headers={
            "accept": "application/json",
            "content-type": "application/json",
        },
        json={"texts": texts},
    )
    if response.ok:
        return response.json()["tensor"]
    else:
        return None


def __get_most_similar_records(
    project_id: str,
    embedding_id: str,
    embedding_tensor: List[float],
    limit: int,
    similarity_filter_option: Optional[List[Dict[str, Any]]] = None,
    threshold: Optional[float] = None,
):
    url = f"{NEURAL_SEARCH}/most_similar_by_embedding?include_scores=true"

    response = requests.post(
        url,
        headers={
            "accept": "application/json",
            "content-type": "application/json",
        },
        json={
            "project_id": project_id,
            "embedding_id": embedding_id,
            "embedding_tensor": embedding_tensor,
            "limit": limit,
            "att_filter": similarity_filter_option,
            "threshold": threshold,
        },
    )
    if response.ok:
        return response.json()
    else:
        return None
