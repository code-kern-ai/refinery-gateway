import docker
import json
import os
from typing import List, Tuple
from controller.tokenization.tokenization_service import request_tokenize_project
from submodules.model.business_objects import (
    attribute,
    general,
    project,
    record,
    tokenization,
)
from submodules.model.models import Attribute
from submodules.s3 import controller as s3
from util import daemon

from .util import find_free_name

client = docker.from_env()
image = os.getenv("AC_EXEC_ENV_IMAGE")
exec_env_network = os.getenv("LF_NETWORK")


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

    name = find_free_name(project_id)

    attribute_item: Attribute = attribute.create(
        project_id,
        name,
        relative_position,
        is_primary_key=False,
        user_created=True,
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


def calculate_user_attribute_all_records(project_id: str, attribute_id: str) -> None:
    attribute.update_state_to_usable(project_id, attribute_id, with_commit=True)
    # TODO: implement logic to run attribute calculation exec env and store the result
    # in the database


def calculate_user_attribute_sample_records(
    project_id: str, attribute_id: str
) -> Tuple[List[str], List[str]]:
    attribute_item = attribute.get(project_id, attribute_id)
    sample_record_ids = [
        record_item
        for record_item, in record.get_attribute_calculation_sample_records(project_id)
    ]
    sample_records_doc_bin = tokenization.get_doc_bin_table_to_json(
        project_id=project_id,
        missing_columns="",
        record_ids=sample_record_ids,
    )
    prefixed_doc_bin = f"{attribute_id}_doc_bin.json"
    prefixed_function_name = f"{attribute_id}_fn"
    prefixed_payload = f"{attribute_id}_payload.json"
    project_item = project.get(project_id)
    org_id = str(project_item.organization_id)
    s3.put_object(
        org_id,
        project_id + "/" + prefixed_doc_bin,
        sample_records_doc_bin,
    )
    s3.put_object(
        org_id,
        project_id + "/" + prefixed_function_name,
        attribute_item.source_code,
    )
    command = [
        s3.create_access_link(org_id, project_id + "/" + prefixed_doc_bin),
        s3.create_access_link(org_id, project_id + "/" + prefixed_function_name),
        project_item.tokenizer_blank,
        s3.create_file_upload_link(org_id, project_id + "/" + prefixed_payload),
    ]

    container = client.containers.run(
        image=image,
        command=command,
        remove=True,
        detach=True,
        network=exec_env_network,
    )

    attribute.logs = [
        line.decode("utf-8").strip("\n")
        for line in container.logs(
            stream=True, stdout=True, stderr=True, timestamps=True
        )
    ]
    print(attribute.logs)
    general.commit()

    payload = s3.get_object(org_id, project_id + "/" + prefixed_payload)
    calculated_attributes = json.loads(payload)
    print(list(calculated_attributes.keys()))
    s3.delete_object(org_id, project_id + "/" + prefixed_doc_bin)
    s3.delete_object(org_id, project_id + "/" + prefixed_function_name)
    s3.delete_object(org_id, project_id + "/" + prefixed_payload)

    return list(calculated_attributes.keys()), list(calculated_attributes.values())
