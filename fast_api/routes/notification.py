from fast_api.models import NotificationsBody
from fast_api.routes.client_response import pack_json_result
from fastapi import APIRouter, Body, Request
from controller.notification import manager
from controller.auth import manager as auth_manager
from controller.auth import manager as auth
from submodules.model.business_objects.notification import get_filtered_notification
from submodules.model.util import sql_alchemy_to_dict
from controller.notification.notification_data import __notification_data


router = APIRouter()

NOTIFICATION_WHITELIST = ["message", "level", "id"]


@router.get("")
def get_notification(request: Request):
    info = request.state.info
    user_id = auth.get_user_by_info(info).id
    data = manager.get_notification(user_id)
    data_dict = sql_alchemy_to_dict(data, column_whitelist=NOTIFICATION_WHITELIST)
    return pack_json_result({"data": {"notificationsByUserId": data_dict}})


@router.post("/notifications")
def get_notifications(
    request: Request,
    body: NotificationsBody = Body(...),
):
    for project_id in body.project_filter:
        auth_manager.check_project_access(request.state.info, project_id)

    user = auth_manager.get_user_by_info(request.state.info)

    notifications = get_filtered_notification(
        user,
        body.project_filter,
        body.level_filter,
        body.type_filter,
        body.user_filter,
        body.limit,
    )

    data = sql_alchemy_to_dict(notifications)
    for notification in data:
        notification_data = __notification_data.get(notification["type"])
        notification["docs"] = notification_data["docs"]
        notification["page"] = notification_data["page"]
        notification["title"] = notification_data["title"]

    return pack_json_result({"data": {"notifications": data}})
