import json
from typing import Optional

from controller.auth.kratos import resolve_user_name_and_email_by_id
from fast_api.models import (
    CreatePersonalTokenBody,
    CreateProjectBody,
    CreateSampleProjectBody,
    UpdateProjectNameAndDescriptionBody,
    UpdateProjectStatusBody,
    UpdateProjectTokenizerBody,
    UploadCredentialsAndIdBody,
)
from fastapi import APIRouter, Body, Depends, Request
from fast_api.routes.client_response import pack_json_result
from typing import Dict, List
from controller.auth import manager as auth_manager
from controller.attribute import manager as attr_manager
from controller.labeling_task import manager as task_manager
from controller.upload_task import manager as upload_task_manager
from submodules.model.business_objects import information_source, labeling_task
from submodules.model import enums, events
from submodules.model.business_objects.embedding import get_all_embeddings_by_project_id
from submodules.model.enums import LabelingTaskType
from submodules.model.business_objects.project import get_project_by_project_id_sql
from submodules.model.business_objects.labeling_task import (
    get_labeling_tasks_by_project_id_full,
)
from controller.project import manager
from controller.model_provider import manager as model_manager
from controller.transfer import manager as transfer_manager
from submodules.model.util import (
    pack_edges_node,
    sql_alchemy_to_dict,
    to_frontend_obj_raw,
)
from util import notification, doc_ock
from util.inter_annotator.functions import (
    resolve_inter_annotator_matrix_classification,
    resolve_inter_annotator_matrix_extraction,
)
from controller.misc import manager as misc
from exceptions.exceptions import NotAllowedInOpenSourceError
from submodules.model.business_objects import notification as notification_model

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


@router.get(
    "/{project_id}/project-by-project-id",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_project_by_project_id(
    project_id: str,
) -> Dict:
    data = get_project_by_project_id_sql(project_id)
    return pack_json_result({"data": {"projectByProjectId": data}})


@router.get("/all-projects")
def get_all_projects(request: Request) -> Dict:
    projects = manager.get_all_projects_by_user(
        auth_manager.get_organization_id_by_info(request.state.info)
    )
    projects_packed = pack_edges_node(projects, "allProjects")
    return pack_json_result(projects_packed)


@router.get("/all-projects-mini")
def get_all_projects_mini(request: Request) -> Dict:
    projects = manager.get_all_projects_by_user(
        auth_manager.get_organization_id_by_info(request.state.info)
    )

    edges = []

    for project in projects:
        edges.append(
            {
                "node": {
                    "id": str(project.get("id", None)),
                    "name": str(project.get("name", None)),
                    "description": str(project.get("description", None)),
                    "status": str(project.get("status", None)),
                }
            }
        )

    data = {
        "edges": edges,
    }

    return pack_json_result({"data": {"allProjects": data}})


@router.get(
    "/{project_id}/general-project-stats",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
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


@router.get(
    "/{project_id}/inter-annotator-matrix",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
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
                )
            }
        },
        wrap_for_frontend=False,  # not wrapped as the prepared results in snake_case are still the expected form the frontend
    )


@router.get(
    "/{project_id}/confusion-matrix",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
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


@router.get(
    "/{project_id}/confidence-distribution",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
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


@router.get(
    "/{project_id}/label-distribution",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
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


@router.get(
    "/{project_id}/gates-integration-data",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def gates_integration_data(project_id: str) -> str:
    return pack_json_result(
        {
            "data": {
                "getGatesIntegrationData": manager.get_gates_integration_data(
                    project_id, False
                )
            }
        },
    )


@router.get(
    "/{project_id}/project-tokenization",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def project_tokenization(project_id: str) -> str:
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


@router.get(
    "/{project_id}/labeling-tasks-by-project-id",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def labeling_tasks_by_project_id(project_id: str) -> str:
    return pack_json_result(
        {
            "data": {
                "projectByProjectId": sql_alchemy_to_dict(
                    get_labeling_tasks_by_project_id_full(project_id)
                )
            }
        },
    )


@router.get(
    "/{project_id}/labeling-tasks-by-project-id-with-embeddings",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def labeling_tasks_by_project_id_with_embeddings(
    project_id: str, only_on_attribute: bool = False
) -> str:
    embeddings = get_all_embeddings_by_project_id(project_id)

    embeddings_edges = []
    for embedding in embeddings:
        if (
            only_on_attribute
            and embedding.type != enums.EmbeddingType.ON_ATTRIBUTE.value
        ):
            continue
        attribute = attr_manager.get_attribute(project_id, embedding.attribute_id)
        embeddings_edges.append(
            {
                "node": {
                    "id": str(embedding.id),
                    "name": embedding.name,
                    "state": embedding.state,
                    "attribute": {"dataType": attribute.data_type},
                }
            }
        )

    labeling_tasks_all = labeling_task.get_all(project_id)

    labeling_tasks_edges = []

    for labeling_task_item in labeling_tasks_all:
        information_sources_ids = information_source.get_all_ids_by_labeling_task_id(
            project_id, labeling_task_item.id
        )

        information_sources = []
        for information_source_id in information_sources_ids:
            is_val = information_source.get(project_id, information_source_id)
            information_sources.append(is_val)

        information_sources_edges = []
        for information_source_item in information_sources:
            last_payload = information_source.get_last_payload(
                project_id, information_source_item.id
            )
            lastPayload = {}
            if last_payload is not None:
                lastPayload = {"state": last_payload.state}
            information_sources_edges.append(
                {
                    "node": {
                        "id": str(information_source_item.id),
                        "name": information_source_item.name,
                        "description": information_source_item.description,
                        "type": information_source_item.type,
                        "lastPayload": lastPayload,
                    }
                }
            )

        labeling_tasks_edges.append(
            {
                "node": {
                    "id": str(labeling_task_item.id),
                    "name": labeling_task_item.name,
                    "taskType": labeling_task_item.task_type,
                    "informationSources": {"edges": information_sources_edges},
                }
            }
        )

    data = {
        "data": {
            "projectByProjectId": {
                "embeddings": {"edges": embeddings_edges},
                "labelingTasks": {"edges": labeling_tasks_edges},
            }
        }
    }

    return pack_json_result(data)


@router.get(
    "/{project_id}/record-export-by-project-id",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def record_export_by_project_id(project_id: str) -> str:
    data = manager.get_project_with_labeling_tasks_info_attributes(project_id)
    data_packed = pack_edges_node(data, "projectByProjectId")
    return pack_json_result(data_packed)


@router.get("/model-provider-info")
def get_model_provider_info(request: Request) -> Dict:
    if not misc.check_is_managed():
        raise NotAllowedInOpenSourceError

    data = model_manager.get_model_provider_info()
    return pack_json_result({"data": {"modelProviderInfo": data}})


@router.get(
    "/{project_id}/rats-running",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def is_rats_running(
    request: Request,
    project_id: str,
) -> Dict:

    data = manager.is_rats_tokenization_still_running(project_id)
    return pack_json_result({"data": {"isRatsTokenizationStillRunning": data}})


@router.get(
    "/{project_id}/last-export-credentials",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def last_export_credentials(
    request: Request,
    project_id: str,
) -> Dict:

    data = transfer_manager.last_project_export_credentials(project_id)
    return pack_json_result({"data": {"lastProjectExportCredentials": data}})


@router.post(
    "/{project_id}/upload-credentials-and-id",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def upload_credentials_and_id(
    request: Request,
    project_id: str,
    upload_credentials: UploadCredentialsAndIdBody = Body(...),
):
    user_id = auth_manager.get_user_id_by_info(request.state.info)
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


@router.get(
    "/{project_id}/upload-task-by-id",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def upload_task_by_id(
    request: Request,
    project_id: str,
    upload_task_id: str,
) -> Dict:
    if upload_task_id.find("/") != -1:
        upload_task_id = upload_task_id.split("/")[-1]
    data = upload_task_manager.get_upload_task(project_id, upload_task_id)
    data_dict = to_frontend_obj_raw(sql_alchemy_to_dict(data))
    return pack_json_result(
        {"data": {"uploadTaskById": data_dict}}, wrap_for_frontend=False
    )


@router.post(
    "/{project_id}/update-project-name-description",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def update_project_name_description(
    request: Request,
    project_id: str,
    body: UpdateProjectNameAndDescriptionBody = Body(...),
):
    manager.update_project(project_id, name=body.name, description=body.description)
    # one global for e.g notification center
    notification.send_organization_update(
        project_id, f"project_update:{project_id}", True
    )
    # one for the specific project so it's updated
    notification.send_organization_update(project_id, f"project_update:{project_id}")
    return pack_json_result({"data": {"updateProjectNameDescription": {"ok": True}}})


@router.delete(
    "/{project_id}/delete-project",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def delete_project(request: Request, project_id: str):
    manager.update_project(project_id, status=enums.ProjectStatus.IN_DELETION.value)
    user = auth_manager.get_user_by_info(request.state.info)
    project_item = manager.get_project(project_id)
    organization_id = str(project_item.organization_id)
    notification.create_notification(
        enums.NotificationType.PROJECT_DELETED, user.id, None, project_item.name
    )
    notification_model.remove_project_connection_for_last_x(project_id)
    manager.delete_project(project_id)
    notification.send_organization_update(
        project_id, f"project_deleted:{project_id}:{user.id}", True, organization_id
    )
    return pack_json_result({"data": {"deleteProject": {"ok": True}}})


@router.post("/create-project")
def create_project(
    request: Request,
    body: CreateProjectBody = Body(...),
):
    user = auth_manager.get_user_by_info(request.state.info)

    project = manager.create_project(
        str(user.organization_id), body.name, body.description, str(user.id)
    )

    notification.send_organization_update(
        project.id, f"project_created:{str(project.id)}", True
    )

    doc_ock.post_event(
        str(user.id),
        events.CreateProject(
            Name=f"{body.name}-{project.id}", Description=body.description
        ),
    )

    data = {
        "project": {
            "id": str(project.id),
        }
    }

    return pack_json_result({"data": {"createProject": data}})


@router.put(
    "/{project_id}/update-project-tokenizer",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def update_project_tokenizer(
    project_id: str,
    body: UpdateProjectTokenizerBody = Body(...),
):
    manager.update_project(project_id, tokenizer=body.tokenizer)
    return pack_json_result({"data": {"updateProjectTokenizer": {"ok": True}}})


@router.put(
    "/{project_id}/update-project-status",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def update_project_status(
    project_id: str,
    body: UpdateProjectStatusBody = Body(...),
):
    manager.update_project(project_id, status=body.new_status)
    return pack_json_result({"data": {"updateProjectStatus": {"ok": True}}})


@router.post("/create-sample-project")
def create_sample_project(
    request: Request,
    body: CreateSampleProjectBody = Body(...),
):
    user = auth_manager.get_user_by_info(request.state.info)

    project = manager.import_sample_project(
        user.id, str(user.organization_id), body.name, body.project_type
    )

    doc_ock.post_event(
        str(user.id),
        events.CreateProject(
            Name=f"{project.name}-{project.id}", Description=project.description
        ),
    )

    data = {
        "ok": True,
        "project": {
            "id": str(project.id),
            "name": project.name,
            "description": project.description,
        },
    }

    return pack_json_result({"data": {"createSampleProject": data}})
