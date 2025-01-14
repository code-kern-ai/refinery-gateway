from fastapi import APIRouter, Depends, Request, Body
from controller.auth import manager as auth_manager
from fast_api.routes.client_response import pack_json_result, GENERIC_FAILURE_RESPONSE
from fast_api.models import SearchQuestionBody
from typing import List, Any, Optional, Tuple, Dict
import os
import requests

NEURAL_SEARCH = os.getenv("NEURAL_SEARCH")
EMBEDDING_SERVICE = os.getenv("EMBEDDING_SERVICE")

router = APIRouter()
LIMIT = 10
FILTER = None
THRESHOLD = None


@router.post(
    "/{project_id}/question-playground"
)  # dependencies=[Depends(auth_manager.check_project_access_dep)]
def get_search_results(
    request: Request,
    project_id: str,
    search_question: SearchQuestionBody = Body(...),
):
    embedding_id = search_question.embeddingId
    question = search_question.question

    question_tensor = get_tensors_for_texts(project_id, embedding_id, [question])

    if question_tensor is None:
        return GENERIC_FAILURE_RESPONSE
    elif len(question_tensor) == 0:
        return pack_json_result([])
    search_results = get_most_similar_records(
        project_id, embedding_id, question_tensor[0], LIMIT
    )

    return pack_json_result(search_results)


def get_tensors_for_texts(
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


def get_most_similar_records(
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


@router.post(
    "/{project_id}/store-eval-set"
)  # dependencies=[Depends(auth_manager.check_project_access_dep)]
def store_eval_set(
    request: Request,
    project_id: str,
    search_question: SearchQuestionBody = Body(...),
):
    pass
