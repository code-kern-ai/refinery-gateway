import json
from typing import Optional

from controller.auth.kratos import resolve_user_name_and_email_by_id
from fast_api.models import CreatePersonalTokenBody, UploadCredentialsAndIdBody
from fastapi import APIRouter, Body, Query, Request
from fast_api.routes.client_response import pack_json_result
from typing import Dict, List
from controller.auth import manager as auth_manager
from controller.labeling_task import manager as task_manager
from controller.personal_access_token import manager as token_manager
from controller.upload_task import manager as upload_task_manager
from submodules.model.business_objects.notification import get_filtered_notification
from submodules.model.enums import LabelingTaskType
from submodules.model.business_objects.project import get_project_by_project_id_sql
from submodules.model.business_objects.labeling_task import (
    get_labeling_tasks_by_project_id_full,
)
from controller.project import manager
from controller.model_provider import manager as model_manager
from controller.transfer import manager as transfer_manager
from submodules.model.util import pack_as_graphql, sql_alchemy_to_dict
from util.inter_annotator.functions import (
    resolve_inter_annotator_matrix_classification,
    resolve_inter_annotator_matrix_extraction,
)
from controller.misc import manager as misc
from exceptions.exceptions import NotAllowedInOpenSourceError

from submodules.model.business_objects import tokenization, task_queue

router = APIRouter()

PROJECT_TOKENIZATION_WHITELIST = {
    "id",
    "project_id",
    "user_id",
    "type",
    "state",
    "progress",
    "workload",
    "started_at",
    "finished_at",
}

TOKENS_WHITELIST = {
    "id",
    "created_at",
    "expires_at",
    "last_used",
    "name",
    "scope",
    "user_id",
}


@router.get("/{project_id}/project-by-project-id")
def get_project_by_project_id(request: Request, project_id: str) -> Dict:
    data = get_project_by_project_id_sql(project_id)
    return pack_json_result({"data": {"projectByProjectId": data}})


@router.get("/all-projects")
def get_all_projects(request: Request) -> Dict:
    organization = auth_manager.get_organization_id_by_info(request.state.info)

    projects = manager.get_all_projects_by_user(organization.id)
    projects_graphql = pack_as_graphql(projects, "allProjects")
    return pack_json_result(projects_graphql)


@router.get("/{project_id}/general-project-stats")
def general_project_stats(
    project_id: str,
    labeling_task_id: Optional[str] = None,
    slice_id: Optional[str] = None,
) -> Dict:

    return pack_json_result(
        {
            "data": {
                "generalProjectStats": manager.get_general_project_stats(
                    project_id, labeling_task_id, slice_id
                )
            }
        },
        wrap_for_frontend=False,  # not wrapped as the prepared results in snake_case are still the expected form the frontend
    )


@router.get("/{project_id}/inter-annotator-matrix")
def inter_annotator_matrix(
    project_id: str,
    labeling_task_id: str,
    include_gold_star: Optional[bool] = True,
    include_all_org_user: Optional[bool] = False,
    only_on_static_slice: Optional[str] = None,
) -> Dict:

    labeling_task = task_manager.get_labeling_task(project_id, labeling_task_id)
    if not labeling_task:
        raise ValueError("Can't match labeling task to given Ids")
    fp = None
    if labeling_task.task_type == LabelingTaskType.CLASSIFICATION.value:
        fp = resolve_inter_annotator_matrix_classification
    elif labeling_task.task_type == LabelingTaskType.INFORMATION_EXTRACTION.value:
        fp = resolve_inter_annotator_matrix_extraction
    else:
        raise ValueError(f"Can't match task type {labeling_task.task_type}")

    return pack_json_result(
        {
            "data": {
                "interAnnotatorMatrix": fp(
                    labeling_task,
                    include_gold_star,
                    include_all_org_user,
                    only_on_static_slice,
                    as_gql_type=False,
                )
            }
        },
        wrap_for_frontend=False,  # not wrapped as the prepared results in snake_case are still the expected form the frontend
    )


@router.get("/{project_id}/confusion-matrix")
def confusion_matrix(
    project_id: str,
    labeling_task_id: str,
    slice_id: Optional[str] = None,
) -> Dict:
    return pack_json_result(
        {
            "data": {
                "confusionMatrix": manager.get_confusion_matrix(
                    project_id, labeling_task_id, slice_id
                )
            }
        },
        wrap_for_frontend=False,  # not wrapped as the prepared results in snake_case are still the expected form the frontend
    )


@router.get("/{project_id}/confidence-distribution")
def confidence_distribution(
    project_id: str,
    labeling_task_id: Optional[str] = None,
    slice_id: Optional[str] = None,
    num_samples: int = 100,
) -> List:
    return pack_json_result(
        {
            "data": {
                "confidenceDistribution": manager.get_confidence_distribution(
                    project_id, labeling_task_id, slice_id, num_samples
                )
            }
        },
        wrap_for_frontend=False,  # not wrapped as the prepared results in snake_case are still the expected form the frontend
    )


@router.get("/{project_id}/label-distribution")
def label_distribution(
    project_id: str,
    labeling_task_id: Optional[str] = None,
    slice_id: Optional[str] = None,
) -> str:
    return pack_json_result(
        {
            "data": {
                "labelDistribution": manager.get_label_distribution(
                    project_id, labeling_task_id, slice_id
                )
            }
        },
        wrap_for_frontend=False,  # not wrapped as the prepared results in snake_case are still the expected form the frontend
    )


@router.get("/{project_id}/gates-integration-data")
def gates_integration_data(
    project_id: str,
) -> str:
    return pack_json_result(
        {
            "data": {
                "getGatesIntegrationData": manager.get_gates_integration_data(
                    project_id, False
                )
            }
        },
    )


@router.get("/{project_id}/project-tokenization")
def project_tokenization(
    project_id: str,
) -> str:
    waiting_task = task_queue.get_by_tokenization(project_id)
    data = None
    if waiting_task and not waiting_task.is_active:
        data = {
            "id": waiting_task.id,
            "started_at": waiting_task.created_at,
            "state": "QUEUED",
            "progress": -1,
        }
        for key in PROJECT_TOKENIZATION_WHITELIST:
            if key not in data:
                data[key] = None
    else:
        data = sql_alchemy_to_dict(
            tokenization.get_record_tokenization_task(project_id),
            column_whitelist=PROJECT_TOKENIZATION_WHITELIST,
        )
    return pack_json_result(
        {"data": {"projectTokenization": data}},
    )


@router.get("/{project_id}/labeling-tasks-by-project-id")
def labeling_tasks_by_project_id(
    project_id: str,
) -> str:
    return pack_json_result(
        {
            "data": {
                "projectByProjectId": sql_alchemy_to_dict(
                    get_labeling_tasks_by_project_id_full(project_id)
                )
            }
        },
    )


@router.get("/{project_id}/record-export-by-project-id")
def record_export_by_project_id(
    project_id: str,
) -> str:
    data = manager.get_project_with_labeling_tasks_info_attributes(project_id)
    data_graphql = pack_as_graphql(data, "projectByProjectId")
    return pack_json_result(data_graphql)


@router.get("/model-provider-info")
def get_model_provider_info(request: Request) -> Dict:
    if not misc.check_is_managed():
        raise NotAllowedInOpenSourceError

    data = model_manager.get_model_provider_info()
    return pack_json_result({"data": {"modelProviderInfo": data}})


@router.get("/{project_id}/rats-running")
def is_rats_running(request: Request, project_id: str) -> Dict:

    data = manager.is_rats_tokenization_still_running(project_id)
    return pack_json_result({"data": {"isRatsTokenizationStillRunning": data}})


@router.get("/{project_id}/access-tokens")
def get_access_tokens(request: Request, project_id: str) -> Dict:
    data = sql_alchemy_to_dict(
        token_manager.get_all_personal_access_tokens(project_id),
        column_whitelist=TOKENS_WHITELIST,
    )
    for token in data:
        names, email = resolve_user_name_and_email_by_id(token["user_id"])
        last_name = names.get("last", "")
        first_name = names.get("first", "")
        token["created_by"] = f"{first_name} {last_name}"

    return pack_json_result({"data": {"allPersonalAccessTokens": data}})


@router.get("/{project_id}/last-export-credentials")
def last_export_credentials(request: Request, project_id: str) -> Dict:

    data = transfer_manager.last_project_export_credentials(project_id)
    return pack_json_result({"data": {"lastProjectExportCredentials": data}})


@router.post("/{project_id}/upload-credentials-and-id")
def upload_credentials_and_id(
    request: Request,
    project_id: str,
    upload_credentials: UploadCredentialsAndIdBody = Body(...),
):
    user_id = auth_manager.get_user_by_info(request.state.info).id
    data = transfer_manager.get_upload_credentials_and_id(
        project_id,
        user_id,
        upload_credentials.file_name,
        upload_credentials.file_type,
        upload_credentials.file_import_options,
        upload_credentials.upload_type,
        upload_credentials.key,
    )
    return pack_json_result({"data": {"uploadCredentialsAndId": json.dumps(data)}})


@router.get("/{project_id}/upload-task-by-id")
def upload_task_by_id(request: Request, project_id: str, upload_task_id: str) -> Dict:
    if upload_task_id.find("/") != -1:
        upload_task_id = upload_task_id.split("/")[-1]
    data = upload_task_manager.get_upload_task(project_id, upload_task_id)
    return {"data": {"uploadTaskById": data}}


@router.get("/notifications")
def get_notifications(
    request: Request,
    project_filter: List[str] = Query(default=None),
    level_filter: List[str] = Query(default=None),
    type_filter: List[str] = Query(default=None),
    user_filter: bool = Query(default=True),
    limit: int = Query(default=50),
):

    if project_filter is None:
        project_filter = []
    if level_filter is None:
        level_filter = []
    if type_filter is None:
        type_filter = []

    for project_id in project_filter:
        auth_manager.check_project_access(request.state.info, project_id)

    user = auth_manager.get_user_by_info(request.state.info)
    notifications = get_filtered_notification(
        user, project_filter, level_filter, type_filter, user_filter, limit
    )

    data = sql_alchemy_to_dict(notifications)

    return pack_json_result({"data": {"notifications": data}})


@router.post("/{project_id}/create-personal-token")
def create_personal_access_token(
    request: Request, project_id: str, body: CreatePersonalTokenBody = Body(...)
):
    auth_manager.check_admin_access(request.state.info)
    user_id = auth_manager.get_user_by_info(request.state.info).id
    token = token_manager.create_personal_access_token(
        project_id, user_id, body.name, body.scope, body.expires_at
    )
    return pack_json_result({"data": {"createPersonalAccessToken": token}})


@router.delete("/{project_id}/{token_id}/delete-personal-token")
def delete_personal_access_token(request: Request, project_id: str, token_id: str):
    auth_manager.check_admin_access(request.state.info)
    token_manager.delete_personal_access_token(project_id, token_id)
    return pack_json_result({"data": {"deletePersonalAccessToken": True}})
