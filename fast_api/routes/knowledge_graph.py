from controller.knowledge_graph import manager as knowledge_graph_manager
from controller.auth import manager as auth_manager
from fast_api.models import (
    KnowledgeGraphCreateRequest,
    KnowledgeGraphDeleteRequest,
)
from fastapi import APIRouter, Request
from fast_api.routes.client_response import get_silent_success, pack_json_result

router = APIRouter()


@router.get("/{knowledge_graph_id}")
def get(request: Request, knowledge_graph_id: str):
    user = auth_manager.get_user_by_info(request.state.info)
    return pack_json_result(
        knowledge_graph_manager.get(user.organization_id, knowledge_graph_id)
    )


@router.get("/project/{project_id}")
def get_by_project_id(request: Request, project_id: str):
    user = auth_manager.get_user_by_info(request.state.info)
    return pack_json_result(
        knowledge_graph_manager.get_by_project_id(user.organization_id, project_id)
    )


@router.get("/data/{project_id}")
def get_data(request: Request, project_id: str):
    user = auth_manager.get_user_by_info(request.state.info)
    return pack_json_result(
        knowledge_graph_manager.get_data(user.organization_id, project_id)
    )


@router.post("/")
def create(request: Request, data: KnowledgeGraphCreateRequest):
    user = auth_manager.get_user_by_info(request.state.info)
    knowledge_graph_manager.create_graph(
        user.organization_id,
        user.id,
        data.project_id,
        data.name,
        data.description,
        data.type,
    )
    return get_silent_success()


@router.delete("/{project_id}")
def delete_many(request: Request, project_id: str, data: KnowledgeGraphDeleteRequest):
    user = auth_manager.get_user_by_info(request.state.info)
    knowledge_graph_manager.delete_many(user.organization_id, project_id, data.ids)
    return get_silent_success()
