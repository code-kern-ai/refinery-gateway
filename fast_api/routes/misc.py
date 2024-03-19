from fastapi import APIRouter, Request
from fast_api.routes.client_response import pack_json_result
from typing import Dict
from controller.auth import manager as auth


router = APIRouter()


@router.get("/is-admin")
def get_is_admin(request: Request) -> Dict:
    data = auth.check_is_admin(request)
    return pack_json_result({"data": {"isAdmin": data}})
