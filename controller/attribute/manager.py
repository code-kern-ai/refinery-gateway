from typing import List, Tuple
from controller.tokenization.tokenization_service import request_tokenize_project
from submodules.model.business_objects import attribute, record, tokenization
from submodules.model.models import Attribute
from submodules.model.enums import AttributeState, DataTypes
from util import daemon, notification

from . import util


def get_attribute(project_id: str, attribute_id: str) -> Attribute:
    return attribute.get(project_id, attribute_id)


def get_all_attributes(
    project_id: str, state_filter: List[str] = None
) -> List[Attribute]:
    return attribute.get_all_ordered(project_id, True, state_filter)


def check_composite_key(project_id: str) -> bool:
    return attribute.check_composite_key_is_valid(project_id)


def create_attribute(project_id: str, name: str) -> Attribute:
    relative_position: int = attribute.get_relative_position(project_id)
    if relative_position is None:
        relative_position = 1
    else:
        relative_position += 1

    attribute_item: Attribute = attribute.create(
        project_id,
        name,
        relative_position,
        with_commit=True,
    )
    return attribute_item


def create_user_attribute(project_id: str) -> Attribute:
    relative_position: int = attribute.get_relative_position(project_id)
    if relative_position is None:
        relative_position = 1
    else:
        relative_position += 1

    name = util.find_free_name(project_id)

    attribute_item: Attribute = attribute.create(
        project_id,
        name,
        relative_position,
        data_type=DataTypes.TEXT.value,
        is_primary_key=False,
        user_created=True,
        state=AttributeState.INITIAL.value,
        with_commit=True,
    )

    return attribute_item


def update_attribute(
    project_id: str,
    attribute_id: str,
    data_type: str,
    is_primary_key: bool,
    name: str,
    source_code: str,
) -> None:
    attribute.update(
        project_id,
        attribute_id,
        data_type,
        is_primary_key,
        name,
        source_code,
        with_commit=True,
    )


def delete_attribute(project_id: str, attribute_id: str) -> None:
    attribute_item = attribute.get(project_id, attribute_id)
    if attribute_item.user_created:
        if attribute_item.state == AttributeState.USABLE.value:
            record.delete_user_created_attribute(
                project_id=project_id, attribute_id=attribute_id, with_commit=True
            )
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


def calculate_user_attribute_all_records(
    project_id: str, user_id: str, attribute_id: str
) -> None:
    attribute.update(
        project_id=project_id,
        attribute_id=attribute_id,
        state=AttributeState.RUNNING.value,
        with_commit=True,
    )
    daemon.run(
        __calculate_user_attribute_all_records,
        project_id,
        user_id,
        attribute_id,
    )


def __calculate_user_attribute_all_records(
    project_id: str, user_id: str, attribute_id: str
) -> None:

    calculated_attributes = util.run_attribute_calculation_exec_env(
        attribute_id=attribute_id, project_id=project_id, doc_bin="docbin_full"
    )

    util.add_log_to_attribute_logs(
        project_id, attribute_id, "Writing results to the database."
    )
    # add calculated attributes to database
    record.update_add_user_created_attribute(
        project_id=project_id,
        attribute_id=attribute_id,
        calculated_attributes=calculated_attributes,
        with_commit=True,
    )
    util.add_log_to_attribute_logs(project_id, attribute_id, "Finished writing.")

    util.add_log_to_attribute_logs(
        project_id, attribute_id, "Tokenizing the attribute."
    )
    tokenization.delete_docbins(project_id, with_commit=True)
    tokenization.delete_token_statistics_for_project(project_id, with_commit=True)
    request_tokenize_project(project_id, user_id)
    util.add_log_to_attribute_logs(project_id, attribute_id, "Finished tokenizing.")

    attribute.update(
        project_id=project_id,
        attribute_id=attribute_id,
        state=AttributeState.USABLE.value,
        with_commit=True,
    )

    notification.send_organization_update(
        project_id, f"calculate_attribute:finished:{attribute_id}"
    )


def calculate_user_attribute_sample_records(
    project_id: str, attribute_id: str
) -> Tuple[List[str], List[str]]:
    doc_bin_samples = util.prepare_sample_records_doc_bin(
        attribute_id=attribute_id, project_id=project_id
    )
    calculated_attributes = util.run_attribute_calculation_exec_env(
        attribute_id=attribute_id, project_id=project_id, doc_bin=doc_bin_samples
    )
    return list(calculated_attributes.keys()), list(calculated_attributes.values())
