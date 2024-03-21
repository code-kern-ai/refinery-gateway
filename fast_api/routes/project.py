from typing import Optional

from fastapi import APIRouter, Request
from fast_api.routes.client_response import pack_json_result
from typing import Dict, List
from controller.auth import manager as auth_manager
from controller.labeling_task import manager as task_manager
from submodules.model.enums import LabelingTaskType
from submodules.model.business_objects.project import get_project_by_project_id_sql
from controller.project import manager
from submodules.model.util import pack_as_graphql
from util.inter_annotator.functions import (
    resolve_inter_annotator_matrix_classification,
    resolve_inter_annotator_matrix_extraction,
)


router = APIRouter()


@router.get("/{project_id}/project-by-project-id")
def get_project_by_project_id(
    request: Request, project_id: str, labeling_tasks=False
) -> Dict:

    if labeling_tasks:
        data = manager.get_project_with_labeling_tasks(project_id)
        data_graphql = pack_as_graphql(data, "projectByProjectId")
        return pack_json_result(data_graphql)
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
