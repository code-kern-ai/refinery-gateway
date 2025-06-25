from fastapi import APIRouter, Request

from controller.auth import manager as auth_manager
from controller.project import manager
from fast_api.models import ProjectDeletion
from fast_api.routes.client_response import get_silent_success
from util import notification

from submodules.model import enums
from submodules.model.business_objects import notification as notification_model

router = APIRouter()


@router.delete(
    "/delete-projects",
)
def delete_project(request: Request, data: ProjectDeletion):
    for project_id in data.project_ids:
        manager.update_project(project_id, status=enums.ProjectStatus.IN_DELETION.value)
        user = auth_manager.get_user_by_info(data.user_id)
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
    return get_silent_success()
