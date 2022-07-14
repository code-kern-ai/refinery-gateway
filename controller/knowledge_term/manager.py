from typing import List

from submodules.model import KnowledgeTerm, KnowledgeBase
from submodules.model.enums import NotificationType
from submodules.model.exceptions import (
    EntityAlreadyExistsException,
    EntityNotFoundException,
)
from submodules.model.business_objects import general, knowledge_term, knowledge_base
from util.notification import create_notification


def get_terms_by_knowledge_base(
    project_id: str, knowledge_base_id: str
) -> List[KnowledgeTerm]:
    knowledge_base_item: KnowledgeBase = knowledge_base.get(
        project_id, knowledge_base_id
    )
    if not knowledge_base_item:
        raise EntityNotFoundException

    return knowledge_term.get_by_knowledge_base(knowledge_base_id)


def create_term(
    user_id: str, project_id: str, knowledge_base_id: str, value: str, comment: str
) -> None:
    try:
        knowledge_base_item = knowledge_base.get(project_id, knowledge_base_id)
        if not knowledge_base_item:
            raise EntityNotFoundException

        knowledge_term.create(
            project_id, knowledge_base_id, value, comment, with_commit=True
        )
    except EntityAlreadyExistsException:
        base = knowledge_base.get(project_id, knowledge_base_id)
        create_notification(
            NotificationType.TERM_ALREADY_EXISTS,
            user_id,
            project_id,
            value,
            base.name,
        )


def paste_knowledge_terms(
    project_id: str, knowledge_base_id: str, values: str, split: str, delete: bool
) -> None:
    knowledge_base_item = knowledge_base.get(project_id, knowledge_base_id)
    if not knowledge_base_item:
        raise EntityNotFoundException
    split = split.replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "\r")

    existing_items = knowledge_term.get_by_knowledge_base(knowledge_base_id)
    existing_names = {str(row.value) for row in existing_items}
    value_list = {v.strip() for v in values.split(split) if len(v.strip()) > 0}
    if delete:
        to_remove = existing_names & value_list
        knowledge_term.delete_by_value_list(
            knowledge_base_id, to_remove, with_commit=True
        )
    else:
        to_add = value_list - existing_names
        knowledge_term.create_by_value_list(
            project_id, knowledge_base_id, to_add, with_commit=True
        )


def create_term_in_named_knowledge_base(project_id: str, name: str, value: str) -> None:
    base = knowledge_base.get_by_name(project_id, name)
    if not base:
        base = knowledge_base.create(project_id, name)
    try:
        knowledge_term.create(project_id, base.id, value, None, with_commit=True)
    except EntityAlreadyExistsException:
        pass  # TODO EXCEPTION HANDLING


def update_term(
    project_id: str,
    knowledge_base_id: str,
    user_id: str,
    term_id: str,
    value: str,
    comment: str,
) -> None:
    knowledge_base_item = knowledge_base.get(project_id, knowledge_base_id)
    if not knowledge_base_item:
        raise EntityNotFoundException

    try:
        knowledge_term.update(
            knowledge_base_item.id, term_id, value, comment, with_commit=True
        )
    except EntityAlreadyExistsException:
        create_notification(
            NotificationType.TERM_ALREADY_EXISTS,
            user_id,
            knowledge_base_item.project_id,
            value,
            knowledge_base_item.name,
        )


def delete_term(project_id: str, term_id: str) -> None:
    base = knowledge_base.get_by_term(project_id, term_id)
    if not base:
        raise EntityNotFoundException

    knowledge_term.delete(term_id, with_commit=True)


def blacklist_term(term_id: str) -> None:
    knowledge_term.blacklist(term_id, with_commit=True)
