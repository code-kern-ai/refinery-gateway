from tokenize import String
from typing import List
from controller.tokenization.tokenization_service import request_tokenize_project
from submodules.model.business_objects import attribute, general
from submodules.model.models import Attribute
from util import daemon


def get_attribute(project_id: str, attribute_id: str) -> Attribute:
    return attribute.get(project_id, attribute_id)


def get_all_attributes(project_id: str) -> List[Attribute]:
    return attribute.get_all_ordered(project_id, True)


def check_composite_key(project_id: str) -> bool:
    return attribute.check_composite_key_is_valid(project_id)


def create_attribute(project_id: str, name: str) -> Attribute:
    relative_position: int = attribute.get_relative_position(project_id)
    if relative_position is None:
        relative_position = 1
    else:
        relative_position += 1

    attributeEntity: Attribute =  attribute.create(project_id, name, relative_position, with_commit=True, is_created=True)
    return attributeEntity


def update_attribute(
    project_id: str, attribute_id: str, data_type: str, is_primary_key: bool
) -> None:
    attribute.update(
        project_id, attribute_id, data_type, is_primary_key, with_commit=True
    )


def delete_attribute(project_id: str, attribute_id: str) -> None:
    attribute.delete(project_id, attribute_id, with_commit=True)


def add_running_id(
    user_id: str, project_id: str, attribute_name: str, for_retokenization: bool = True
) -> None:
    if attribute.get_by_name(project_id, attribute_name):
        raise ValueError(f"attribute with name {attribute_name} already exists")

    attribute.add_running_id(
        project_id, attribute_name, for_retokenization, with_commit=True
    )
    if for_retokenization:

        daemon.run(
            request_tokenize_project,
            project_id,
            user_id,
        )
