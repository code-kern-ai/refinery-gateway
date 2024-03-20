from fast_api.routes.client_response import pack_json_result
from fastapi import APIRouter, Request
from controller.notification import manager

router = APIRouter()


@router.get("")
def get_notification(request: Request):
    user_id = request.state.user_id
    data = manager.get_notification(user_id)
    return pack_json_result({"data": {"notificationsByUserId": data}})
