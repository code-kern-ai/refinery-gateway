import json
from typing import Optional

from fast_api.models import (
    CreateProjectBody,
    CreateSampleProjectBody,
    UpdateProjectNameAndDescriptionBody,
    UpdateProjectStatusBody,
    UpdateProjectTokenizerBody,
    UploadCredentialsAndIdBody,
)
from fastapi import APIRouter, Body, Depends, Request
from fast_api.routes.client_response import pack_json_result
from typing import Dict
from controller.auth import manager as auth_manager
from controller.upload_task import manager as upload_task_manager
from submodules.model.business_objects import labeling_task
from submodules.model import enums
from submodules.model.business_objects.project import get_project_by_project_id_sql
from controller.project import manager
from controller.model_provider import manager as model_manager
from controller.transfer import manager as transfer_manager
from submodules.model.util import (
    sql_alchemy_to_dict,
    to_frontend_obj_raw,
)
from util import notification
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
    return pack_json_result(data)


@router.get("/all-projects")
def get_all_projects(request: Request) -> Dict:
    projects = manager.get_all_projects_by_user(
        auth_manager.get_organization_id_by_info(request.state.info)
    )
    return pack_json_result(projects)


@router.get("/all-projects-mini")
def get_all_projects_mini(request: Request) -> Dict:
    projects = manager.get_all_projects_by_user(
        auth_manager.get_organization_id_by_info(request.state.info)
    )

    project_extended = []

    for project in projects:
        project_extended.append(
            {
                "id": str(project.get("id", None)),
                "name": str(project.get("name", None)),
                "description": str(project.get("description", None)),
                "status": str(project.get("status", None)),
            }
        )

    return pack_json_result(project_extended)


@router.get(
    "/{project_id}/general-project-stats",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def general_project_stats(
    project_id: str,
    labeling_task_id: Optional[str] = None,
    slice_id: Optional[str] = None,
) -> Dict:
    data = manager.get_general_project_stats(project_id, labeling_task_id, slice_id)
    return pack_json_result(
        data,
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
    data = manager.get_label_distribution(project_id, labeling_task_id, slice_id)
    return pack_json_result(
        data,
        wrap_for_frontend=False,  # not wrapped as the prepared results in snake_case are still the expected form the frontend
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
    return pack_json_result(data)


@router.get(
    "/{project_id}/labeling-tasks-by-project-id",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def labeling_tasks_by_project_id(project_id: str) -> str:
    data = labeling_task.get_labeling_tasks_by_project_id_full(project_id)
    return pack_json_result(data)


@router.get(
    "/{project_id}/record-export-by-project-id",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def record_export_by_project_id(project_id: str) -> str:
    data = manager.get_project_with_labeling_tasks_info_attributes(project_id)
    return pack_json_result(data)


@router.get("/model-provider-info")
def get_model_provider_info(request: Request) -> Dict:
    data = model_manager.get_model_provider_info()
    return pack_json_result(data)


@router.get(
    "/{project_id}/last-export-credentials",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def last_export_credentials(
    request: Request,
    project_id: str,
) -> Dict:

    data = transfer_manager.last_project_export_credentials(project_id)
    return pack_json_result(data)


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
    return pack_json_result(json.dumps(data))


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
    return pack_json_result(data_dict, wrap_for_frontend=False)


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
    return pack_json_result({"ok": True})


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
    return pack_json_result({"ok": True})


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

    data = {
        "project": {
            "id": str(project.id),
        }
    }

    return pack_json_result(data)


@router.put(
    "/{project_id}/update-project-tokenizer",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def update_project_tokenizer(
    project_id: str,
    body: UpdateProjectTokenizerBody = Body(...),
):
    manager.update_project(project_id, tokenizer=body.tokenizer)
    return pack_json_result({"ok": True})


@router.put(
    "/{project_id}/update-project-status",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def update_project_status(
    project_id: str,
    body: UpdateProjectStatusBody = Body(...),
):
    manager.update_project(project_id, status=body.new_status)
    return pack_json_result({"ok": True})


@router.post("/create-sample-project")
def create_sample_project(
    request: Request,
    body: CreateSampleProjectBody = Body(...),
):
    user = auth_manager.get_user_by_info(request.state.info)

    project = manager.import_sample_project(
        user.id, str(user.organization_id), body.name, body.project_type
    )

    data = {
        "ok": True,
        "project": {
            "id": str(project.id),
            "name": project.name,
            "description": project.description,
        },
    }

    return pack_json_result(data)
