from controller.data_block import manager as data_block_manager
from controller.auth import manager as auth_manager
from fast_api.models import (
    DataBlockCreateRequest,
    DataBlockUpdateRequest,
    DataBlockDeleteRequest,
)
from fastapi import APIRouter, Request
from fast_api.routes.client_response import get_silent_success, pack_json_result

router = APIRouter()


@router.get("/{data_block_id}")
def get(request: Request, data_block_id: str):
    user = auth_manager.get_user_by_info(request.state.info)
    return pack_json_result(data_block_manager.get(user.organization_id, data_block_id))


@router.get("/project/{project_id}")
def get_by_project_id(request: Request, project_id: str):
    user = auth_manager.get_user_by_info(request.state.info)
    return pack_json_result(
        data_block_manager.get_by_project_id(user.organization_id, project_id)
    )


@router.post("/data/{data_block_id}")
def get_data(request: Request, data_block_id: str):
    user = auth_manager.get_user_by_info(request.state.info)
    return pack_json_result(
        data_block_manager.get_data(user.organization_id, data_block_id)
    )


@router.post("/")
def create(request: Request, data: DataBlockCreateRequest):
    user = auth_manager.get_user_by_info(request.state.info)
    data_block = data_block_manager.create(
        user.organization_id,
        user.id,
        data.project_id,
        data.name,
        data.description,
        data.type,
    )
    return pack_json_result({"id": str(data_block.id)}, wrap_for_frontend=False)


@router.put("/{data_block_id}")
def update(request: Request, data_block_id: str, data: DataBlockUpdateRequest):
    user = auth_manager.get_user_by_info(request.state.info)
    data_block_manager.update(
        user.organization_id,
        user.id,
        data_block_id,
        data.name,
        data.description,
    )
    return get_silent_success()


@router.delete("/{project_id}")
def delete_many(request: Request, project_id: str, data: DataBlockDeleteRequest):
    user = auth_manager.get_user_by_info(request.state.info)
    data_block_manager.delete_many(user.organization_id, project_id, data.ids)
    return get_silent_success()
