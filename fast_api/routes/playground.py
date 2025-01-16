from fastapi import APIRouter, Depends, Request, Body
from controller.auth import manager as auth_manager
from fast_api.routes.client_response import pack_json_result
from fast_api.models import SearchQuestionBody, SearchEvalSetBody
from controller.playground import manager as playground_manager

router = APIRouter()


@router.post(
    "/{project_id}/search"
)  # dependencies=[Depends(auth_manager.check_project_access_dep)]
def get_search_results_question(
    request: Request,
    project_id: str,
    search_question: SearchQuestionBody = Body(...),
):
    embedding_id = search_question.embeddingId
    question = search_question.question

    search_results = playground_manager.get_search_result_for_text(
        project_id, embedding_id, question
    )

    return pack_json_result(search_results)


@router.post(
    "/{project_id}/eval-set-search"
)  # dependencies=[Depends(auth_manager.check_project_access_dep)]
def get_search_results_eval_set(
    request: Request,
    project_id: str,
    search_eval_set: SearchEvalSetBody = Body(...),
):
    embedding_id = search_eval_set.embeddingId
    evaluation_set_id = search_eval_set.evalSetId

    search_results = playground_manager.get_search_result_for_evalset(
        project_id, embedding_id, question
    )

    return pack_json_result(search_results)


@router.post(
    "/{project_id}/store-eval-set"
)  # dependencies=[Depends(auth_manager.check_project_access_dep)]
def store_eval_set(
    request: Request,
    project_id: str,
    search_question: SearchQuestionBody = Body(...),
):
    pass
