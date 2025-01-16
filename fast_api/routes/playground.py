from fastapi import APIRouter, Depends, Request, Body
from controller.auth import manager as auth_manager
from fast_api.routes.client_response import pack_json_result, get_silent_success
from fast_api.models import (
    SearchQuestionBody,
    EvaluationSetCreationBody,
    EvaluationGroupCreationBody,
)
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
    "/{project_id}/evaluation-sets"
)  # dependencies=[Depends(auth_manager.check_project_access_dep)]
def create_evaluation_set(
    request: Request,
    project_id: str,
    evaluation_set: EvaluationSetCreationBody = Body(...),
):
    playground_manager.create_evaluation_set(
        project_id, evaluation_set.question, evaluation_set.recordIds
    )
    return get_silent_success()


@router.get(
    "/{project_id}/evaluation-sets"
)  # dependencies=[Depends(auth_manager.check_project_access_dep)]
def get_evaluation_sets(
    request: Request,
    project_id: str,
):
    matching_sets = playground_manager.get_evaluation_sets(project_id)
    return pack_json_result(matching_sets)


@router.get("/{project_id}/evaluation-sets/{set_id}")
def get_single_evaluation_set(
    request: Request,
    project_id: str,
    set_id: str,
):
    matching_set = playground_manager.get_evaluation_set_by_id(project_id, set_id)
    return pack_json_result(matching_set)


@router.post(
    "/{project_id}/evaluation-groups"
)  # dependencies=[Depends(auth_manager.check_project_access_dep)]
def create_evaluation_group(
    request: Request,
    project_id: str,
    evaluation_group: EvaluationGroupCreationBody = Body(...),
):
    playground_manager.create_evaluation_set(
        project_id, evaluation_group.name, evaluation_group.matchingSetIds
    )
    return get_silent_success()


@router.get(
    "/{project_id}/evaluation-groups"
)  # dependencies=[Depends(auth_manager.check_project_access_dep)]
def get_evaluation_groups(request: Request, project_id: str):
    evaluation_groups = playground_manager.get_evaluation_groups(project_id)
    return pack_json_result(evaluation_groups)


@router.get("/{project_id}/evaluation-groups/{group_id}")
def get_single_evaluation_group(
    request: Request,
    project_id: str,
    group_id: str,
):
    evaluation_group = playground_manager.get_evaluation_group_by_id(
        project_id, group_id
    )
    return pack_json_result(evaluation_group)
