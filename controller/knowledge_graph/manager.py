from typing import Dict, List, Union

import os

from submodules.model import RefineryKnowledgeGraph, IntegrationSharepoint
from submodules.model.enums import NotificationType, KnowledgeGraphType
from submodules.model.exceptions import EntityNotFoundException
from submodules.model.business_objects import (
    knowledge_graph as knowledge_graph_db_bo,
    project as project_db_bo,
)
from submodules.model.cognition_objects import integration as integration_db_co
from submodules.model.integration_objects import manager as integration_record_db_io
from submodules.model.util import sql_alchemy_to_dict
from util.notification import create_notification
from util.service_requests import post_call_or_raise

COGNITION_GATEWAY = os.getenv("COGNITION_GATEWAY", "http://cognition-gateway:80")


def get(org_id: str, knowledge_graph_id: str) -> RefineryKnowledgeGraph:
    knowledge_graph: RefineryKnowledgeGraph = knowledge_graph_db_bo.get(
        org_id, knowledge_graph_id
    )
    if knowledge_graph_id and not knowledge_graph:
        raise EntityNotFoundException

    return knowledge_graph


def get_by_project_id(org_id: str, project_id: str) -> List[RefineryKnowledgeGraph]:
    knowledge_graphs: List[RefineryKnowledgeGraph] = (
        knowledge_graph_db_bo.get_by_project_id(org_id, project_id)
    )
    return knowledge_graphs


def get_data(
    org_id: str, project_id: str, search_term: str = ""
) -> Dict[str, List[Union[str, RefineryKnowledgeGraph]]]:
    integrations = integration_db_co.get_all_by_project_id(project_id)
    db_info = integration_record_db_io.get_db_info(IntegrationSharepoint)

    exclude_data_types = ["json"]
    aggregate_data_types = ["integer", "bigint"]
    exclude_group_by_columns = ["id"]
    exclude_aggregate_columns = []

    return {
        "group_by": [
            item["column_name"]
            for item in db_info
            if item["data_type"] not in exclude_data_types + aggregate_data_types
            and item["column_name"] not in exclude_group_by_columns
        ],
        "aggregate_by": [
            item["column_name"]
            for item in db_info
            if item["data_type"] in aggregate_data_types
            and item["column_name"] not in exclude_aggregate_columns
        ],
        "records": sql_alchemy_to_dict(
            integration_record_db_io.get_all_sharepoints_by_integration_ids(
                [str(integration.id) for integration in integrations], search_term
            ),
            for_frontend=True,
        ),
    }


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

    knowledge_graph = knowledge_graph_db_bo.create(
        org_id, user_id, project_id, name, description, type, with_commit=True
    )
    return knowledge_graph


def update_graph(
    org_id: str,
    user_id: str,
    knowledge_graph_id: str,
    name: str,
    description: str,
) -> None:
    knowledge_graph = knowledge_graph_db_bo.get(org_id, knowledge_graph_id)
    if not knowledge_graph:
        create_notification(
            NotificationType.KNOWLEDGE_GRAPH_NOT_FOUND,
            user_id,
            knowledge_graph.project_id,
            knowledge_graph.type.value,
        )
        return
    if not project_db_bo.is_integration_project(
        org_id, str(knowledge_graph.project_id)
    ):
        create_notification(
            NotificationType.KNOWLEDGE_GRAPH_NOT_SUPPORTED,
            user_id,
            knowledge_graph.project_id,
        )
        return

    knowledge_graph_db_bo.update(
        org_id, knowledge_graph_id, name, description, with_commit=True
    )


def delete_many(org_id: str, project_id: str, ids: List[str]) -> None:
    knowledge_graph_db_bo.delete_many(org_id, project_id, ids, with_commit=True)


def execute_question(org_id: str, user_id: str, question: str) -> str:
    knowledge_graph = knowledge_graph_db_bo.get_by_project_id_and_type(
        org_id, None, KnowledgeGraphType.LIVE
    )
    if not knowledge_graph:
        create_notification(
            NotificationType.KNOWLEDGE_GRAPH_NOT_FOUND,
            user_id,
            None,
            KnowledgeGraphType.LIVE.value,
        )
        return ""

    if not project_db_bo.is_integration_project(
        org_id, str(knowledge_graph.project_id)
    ):
        create_notification(
            NotificationType.KNOWLEDGE_GRAPH_NOT_SUPPORTED,
            user_id,
            knowledge_graph.project_id,
        )
        return ""

    response = post_call_or_raise(
        f"{COGNITION_GATEWAY}/api/knowledge-graphs/internal/{knowledge_graph.id}/execute-question",
        {
            "question": question,
        },
    )
    return response["answer"]
