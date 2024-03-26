from fast_api.routes.client_response import pack_json_result
from fastapi import APIRouter, Request
from controller.notification import manager
from controller.auth import manager as auth
from submodules.model.util import sql_alchemy_to_dict


router = APIRouter()

NOTIFICATION_WHITELIST = ["message", "level", "id"]


@router.get("")
def get_notification(request: Request):
    info = request.state.info
    user_id = auth.get_user_by_info(info).id
    data = manager.get_notification(user_id)
    data_dict = sql_alchemy_to_dict(data, column_whitelist=NOTIFICATION_WHITELIST)
    return pack_json_result({"data": {"notificationsByUserId": data_dict}})
