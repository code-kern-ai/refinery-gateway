from typing import List

from submodules.model import RefineryKnowledgeGraph
from submodules.model.enums import NotificationType, KnowledgeGraphType
from submodules.model.exceptions import EntityNotFoundException
from submodules.model.business_objects import (
    knowledge_graph as knowledge_graph_db_bo,
    project as project_db_bo,
)
from submodules.model.cognition_objects import integration as integration_db_co
from submodules.model.integration_objects import manager as integration_record_db_io
from util.notification import create_notification


def get(org_id: str, knowledge_graph_id: str) -> RefineryKnowledgeGraph:
    knowledge_graph: RefineryKnowledgeGraph = knowledge_graph_db_bo.get(
        org_id, knowledge_graph_id
    )
    if not knowledge_graph:
        raise EntityNotFoundException

    return knowledge_graph


def get_by_project_id(org_id: str, project_id: str) -> List[RefineryKnowledgeGraph]:
    knowledge_graphs: List[RefineryKnowledgeGraph] = (
        knowledge_graph_db_bo.get_by_project_id(org_id, project_id)
    )
    # if not knowledge_graphs:
    #     raise EntityNotFoundException

    return knowledge_graphs


def get_data(org_id: str, project_id: str) -> List[RefineryKnowledgeGraph]:
    integrations = integration_db_co.get_all_by_project_id(org_id, project_id)
    if not integrations:
        raise EntityNotFoundException

    return integration_record_db_io.get_all_sharepoints_by_integration_ids(
        [str(integration.id) for integration in integrations]
    )


def create_graph(
    org_id: str,
    user_id: str,
    project_id: str,
    name: str,
    description: str,
    type: KnowledgeGraphType,
) -> None:
    if knowledge_graph_db_bo.get_by_project_id_and_type(org_id, project_id, type):
        create_notification(
            NotificationType.KNOWLEDGE_GRAPH_EXISTS,
            user_id,
            project_id,
            type.value,
        )
        return
    if not project_db_bo.is_integration_project(org_id, project_id):
        create_notification(
            NotificationType.KNOWLEDGE_GRAPH_NOT_SUPPORTED,
            user_id,
            project_id,
        )
        return

    knowledge_graph_db_bo.create(
        org_id, user_id, project_id, name, description, type, with_commit=True
    )


def delete_many(org_id: str, project_id: str, ids: List[str]) -> None:
    knowledge_graph_db_bo.delete_many(org_id, project_id, ids, with_commit=True)
