from typing import List

from submodules.model import KnowledgeBase
from submodules.model.enums import NotificationType
from submodules.model.exceptions import EntityAlreadyExistsException
from submodules.model.business_objects import knowledge_base, general
from util.notification import create_notification
from . import util


def get_knowledge_base(project_id: str, knowledge_base_id: str) -> KnowledgeBase:
    return knowledge_base.get(project_id, knowledge_base_id)


def get_all_knowledge_bases(project_id: str) -> List[KnowledgeBase]:
    return knowledge_base.get_all(project_id)


def get_knowledge_base_by_term(
    project_id: str, knowledge_base_id: str
) -> KnowledgeBase:
    return knowledge_base.get_by_term(project_id, knowledge_base_id)


def create_knowledge_base(project_id: str) -> KnowledgeBase:
    name: str = util.find_free_name(project_id)
    base_item: KnowledgeBase = knowledge_base.create(project_id, name, with_commit=True)
    return base_item


def update_knowledge_base(
    project_id: str, user_id: str, knowledge_base_id: str, name: str, description: str
) -> None:
    try:
        knowledge_base.update(
            project_id, knowledge_base_id, name, description, with_commit=True
        )
    except EntityAlreadyExistsException:
        create_notification(
            NotificationType.KNOWLEDGE_BASE_ALREADY_EXISTS,
            user_id,
            project_id,
            name,
        )


def delete_knowledge_base(project_id: str, knowledge_base_id: str) -> None:
    knowledge_base.delete(project_id, knowledge_base_id, with_commit=True)
