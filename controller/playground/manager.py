from fast_api.routes.client_response import pack_json_result, GENERIC_FAILURE_RESPONSE
from submodules.model.business_objects import (
    evaluation_set,
    evaluation_group,
    evaluation_run,
)
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


def create_evaluation_set(project_id: str, question: str, record_ids: List[str]):
    pass


def get_evaluation_set_by_id(project_id: str, set_id: str):
    return evaluation_set.get(project_id, set_id)


def get_evaluation_sets(project_id: str):
    return evaluation_set.get_all(project_id)


def create_evaluation_group(project_id: str, name: str, evaluation_set_ids: List[str]):
    pass


def get_evaluation_group_by_id(project_id: str, group_id: str):
    return evaluation_group.get(project_id, group_id)


def get_evaluation_groups(project_id: str):
    return evaluation_group.get_all(project_id)


def get_evaluation_runs(project_id: str):
    return evaluation_run.get_all(project_id)


def init_evaluation_run(project_id: str, evaluation_group_id: str):
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
