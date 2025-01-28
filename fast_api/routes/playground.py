from fastapi import APIRouter, Depends, Request, Body
from controller.auth import manager as auth_manager
from fast_api.routes.client_response import (
    pack_json_result,
    get_silent_success,
)
from fast_api.models import (
    EvaluationRunDeletionBody,
    SearchQuestionBody,
    EvaluationSetCreationBody,
    EvaluationGroupCreationBody,
    EvaluationRunCreationBody,
    RecordSearchContains,
    EvaluationSetDeletionBody,
    EvaluationGroupDeletionBody,
)
from controller.playground import manager as playground_manager

router = APIRouter()


@router.post(
    "/{project_id}/search",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_search_results_question(
    request: Request,
    project_id: str,
    search_question: SearchQuestionBody = Body(...),
):
    embedding_id = search_question.embeddingId
    question = search_question.question
    limit = search_question.limit
    filter = search_question.filter
    threshold = search_question.threshold
    search_results = playground_manager.get_search_result_for_text(
        project_id, embedding_id, question, limit, filter, threshold
    )

    return pack_json_result(search_results, wrap_for_frontend=False)


@router.post(
    "/{project_id}/evaluation-sets",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def create_evaluation_set(
    request: Request,
    project_id: str,
    evaluation_set: EvaluationSetCreationBody = Body(...),
):
    user_id = auth_manager.get_user_id_by_info(request.state.info)
    playground_manager.create_evaluation_set(
        project_id,
        evaluation_set.question,
        evaluation_set.recordIds,
        user_id,
    )
    return get_silent_success()


@router.delete(
    "/{project_id}/evaluation-sets"
)  # dependencies=[Depends(auth_manager.check_project_access_dep)]
def delete_evaluation_set(
    request: Request,
    project_id: str,
    evaluation_set: EvaluationSetDeletionBody = Body(...),
):
    playground_manager.delete_evaluation_sets(
        project_id, evaluation_set.evaluationSetIds
    )
    return get_silent_success()


@router.get(
    "/{project_id}/evaluation-sets",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_evaluation_sets(
    request: Request,
    project_id: str,
):
    matching_sets = playground_manager.get_evaluation_sets(project_id)
    return pack_json_result(matching_sets)


@router.get(
    "/{project_id}/evaluation-sets/{set_id}",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_single_evaluation_set(
    request: Request,
    project_id: str,
    set_id: str,
):
    matching_set = playground_manager.get_evaluation_set_by_id(project_id, set_id)
    return pack_json_result(matching_set)


@router.get(
    "/{project_id}/evaluation-sets-by-group/{evaluation_group_id}",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_evaluation_sets_batch(
    request: Request,
    project_id: str,
    evaluation_group_id: str,
):
    evaluation_sets = playground_manager.get_evaluation_sets_by_group_id(
        project_id, evaluation_group_id
    )

    return pack_json_result(evaluation_sets)


@router.post(
    "/{project_id}/evaluation-groups",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def create_evaluation_group(
    request: Request,
    project_id: str,
    evaluation_group: EvaluationGroupCreationBody = Body(...),
):
    user_id = auth_manager.get_user_id_by_info(request.state.info)
    playground_manager.create_evaluation_group(
        project_id,
        evaluation_group.name,
        evaluation_group.evaluationSetIds,
        user_id,
    )
    return get_silent_success()


@router.delete(
    "/{project_id}/evaluation-groups"
)  # dependencies=[Depends(auth_manager.check_project_access_dep)]
def delete_evaluation_group(
    request: Request,
    project_id: str,
    evaluation_group: EvaluationGroupDeletionBody = Body(...),
):
    playground_manager.delete_evaluation_groups(
        project_id, evaluation_group.evaluationGroupIds
    )
    return get_silent_success()


@router.get(
    "/{project_id}/evaluation-groups",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
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


@router.get(
    "/{project_id}/evaluation-runs",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_evaluation_runs(request: Request, project_id: str):
    evaluation_runs = playground_manager.get_evaluation_runs(project_id)
    return pack_json_result(evaluation_runs, wrap_for_frontend=False)


@router.get("/{project_id}/evaluation-runs/{run_id}")
def get_single_evaluation_run(
    request: Request,
    project_id: str,
    run_id: str,
):
    evaluation_run = playground_manager.get_evaluation_run_by_id(project_id, run_id)
    return pack_json_result(evaluation_run, wrap_for_frontend=False)


@router.post(
    "/{project_id}/evaluation-runs",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def create_evaluation_run(
    request: Request,
    project_id: str,
    evaluation_run: EvaluationRunCreationBody = Body(...),
):
    user_id = auth_manager.get_user_id_by_info(request.state.info)
    playground_manager.init_evaluation_run(
        project_id,
        evaluation_run.embeddingId,
        evaluation_run.evaluationGroupId,
        user_id,
    )
    return get_silent_success()


@router.post(
    "/{project_id}/record-search-contains",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_record_by_content(
    request: Request,
    project_id: str,
    record_search: RecordSearchContains = Body(...),
):
    query = record_search.query
    limit = record_search.limit
    offset = record_search.offset
    user = "52a09a36-5e3a-446a-a9b7-0104edecf62d"  # request.state.user
    records = playground_manager.get_records_by_content(
        project_id, user, query, limit, offset
    )
    return pack_json_result(records, wrap_for_frontend=False)


@router.delete(
    "/{project_id}/evaluation-runs",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def delete_evaluation_run(
    request: Request,
    project_id: str,
    evaluation_set: EvaluationRunDeletionBody = Body(...),
):
    playground_manager.delete_evaluation_runs(
        project_id, evaluation_set.evaluationRunIds
    )
    return get_silent_success()
