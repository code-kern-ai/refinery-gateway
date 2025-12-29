from controller.knowledge_graph import manager as knowledge_graph_manager
from fast_api.models import (
    KnowledgeGraphCreateRequest,
    KnowledgeGraphDeleteRequest,
)
from fastapi import APIRouter
from fast_api.routes.client_response import get_silent_success, pack_json_result

router = APIRouter()


@router.get("/{knowledge_graph_id}")
def get(request, knowledge_graph_id: str):
    org_id = request.state.org_id
    return pack_json_result(knowledge_graph_manager.get(org_id, knowledge_graph_id))


@router.get("/project/{project_id}")
def get_by_project_id(request, project_id: str):
    org_id = request.state.org_id
    return pack_json_result(
        knowledge_graph_manager.get_by_project_id(org_id, project_id)
    )


@router.get("/data/{project_id}")
def get_data(request, project_id: str):
    org_id = request.state.org_id
    return pack_json_result(knowledge_graph_manager.get_data(org_id, project_id))


@router.post("/")
def create(request, data: KnowledgeGraphCreateRequest):
    knowledge_graph_manager.create_graph(
        request.state.org_id,
        request.state.user_id,
        data.project_id,
        data.name,
        data.description,
        data.type,
    )
    return get_silent_success()


@router.delete("/{project_id}")
def delete_many(request, project_id: str, data: KnowledgeGraphDeleteRequest):
    knowledge_graph_manager.delete_many(request.state.org_id, project_id, data.ids)
    return get_silent_success()
