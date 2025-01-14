from fastapi import APIRouter, Depends, Request, Body
from controller.auth import manager as auth_manager
from fast_api.routes.client_response import pack_json_result
from fast_api.models import SearchQuestionBody
from typing import List, Any, Optional, Tuple
import os
import requests

NEURAL_SEARCH = os.getenv("NEURAL_SEARCH")
EMBEDDING_SERVICE = os.getenv("EMBEDDING_SERVICE")

router = APIRouter()


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

    has_error, result, logs = get_tensors_for_texts(
        project_id, embedding_id, [question]
    )
    return pack_json_result({"has_error": has_error, "result": result, "logs": logs})


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


@router.post(
    "/{project_id}/store-eval-set"
)  # dependencies=[Depends(auth_manager.check_project_access_dep)]
def store_eval_set(
    request: Request,
    project_id: str,
    search_question: SearchQuestionBody = Body(...),
):
    pass
