from fastapi import APIRouter, Body, Request
from exceptions.exceptions import ProjectAccessError
from fast_api.models import ModelProviderDeleteModelBody
from fast_api.routes.client_response import pack_json_result
from typing import Dict
from controller.auth import manager as auth
from controller.misc import manager
from controller.misc import manager as misc
from controller.model_provider import manager as model_provider_manager

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


@router.delete("/model-provider-delete-model")
def model_provider_delete_model(
    request: Request, body: ModelProviderDeleteModelBody = Body(...)
):
    if misc.check_is_managed():
        if not auth.check_is_single_organization():
            auth.check_admin_access(request.state.info)
    else:
        raise ProjectAccessError("Not allowed in open source version.")
    model_provider_manager.model_provider_delete_model(body.model_name)

    return pack_json_result({"data": {"modelProviderDeleteModel": {"ok": True}}})
