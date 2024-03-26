from fastapi import APIRouter, Request
from fast_api.routes.client_response import pack_json_result
from typing import Dict
from controller.auth import manager as auth
from controller.misc import config_service, manager

router = APIRouter()


@router.get("/is-admin")
def get_is_admin(request: Request) -> Dict:
    data = auth.check_is_admin(request)
    return pack_json_result({"data": {"isAdmin": data}})


@router.get("/version-overview")
def get_version_overview(request: Request) -> Dict:
    data = manager.get_version_overview()
    return pack_json_result({"data": {"versionOverview": data}})


@router.get("/has-updates")
def has_updates(request: Request) -> Dict:
    data = manager.has_updates()
    return pack_json_result({"data": {"hasUpdates": data}})
