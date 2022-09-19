import docker
import json
import os
from submodules.model.business_objects import attribute, record, project, tokenization
from submodules.s3 import controller as s3

client = docker.from_env()
image = os.getenv("AC_EXEC_ENV_IMAGE")
exec_env_network = os.getenv("LF_NETWORK")


def find_free_name(project_id: str, counter: int = 0) -> str:
    bases_count: int = attribute.count(project_id)
    name: str = f"attribute_{counter}{bases_count}"

    if attribute.get_by_name(project_id, name) is not None:
        return find_free_name(project_id, counter + 1)
    else:
        return name


def prepare_sample_records_doc_bin(attribute_id: str, project_id: str) -> str:

    sample_record_ids = [
        record_item
        for record_item, in record.get_attribute_calculation_sample_records(project_id)
    ]
    sample_records_doc_bin = tokenization.get_doc_bin_table_to_json(
        project_id=project_id,
        missing_columns="",
        record_ids=sample_record_ids,
    )
    project_item = project.get(project_id)
    org_id = str(project_item.organization_id)
    prefixed_doc_bin = f"{attribute_id}_doc_bin.json"
    s3.put_object(
        org_id,
        project_id + "/" + prefixed_doc_bin,
        sample_records_doc_bin,
    )
    return prefixed_doc_bin


def run_attribute_calculation_exec_env(
    attribute_id: str, project_id: str, doc_bin: str
) -> None:

    attribute_item = attribute.get(project_id, attribute_id)

    prefixed_function_name = f"{attribute_id}_fn"
    prefixed_payload = f"{attribute_id}_payload.json"
    project_item = project.get(project_id)
    org_id = str(project_item.organization_id)

    s3.put_object(
        org_id,
        project_id + "/" + prefixed_function_name,
        attribute_item.source_code,
    )
    command = [
        s3.create_access_link(org_id, project_id + "/" + doc_bin),
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

    logs = [
        line.decode("utf-8").strip("\n")
        for line in container.logs(
            stream=True, stdout=True, stderr=True, timestamps=True
        )
    ]

    attribute.update(
        project_id=project_id, attribute_id=attribute_id, logs=logs, with_commit=True
    )

    try:
        payload = s3.get_object(org_id, project_id + "/" + prefixed_payload)
        calculated_attributes = json.loads(payload)
    except s3.error.located_error.GraphQLLocatedError:
        calculated_attributes = {}

    if not doc_bin == "docbin_full":
        # sample records docbin should be delteted after calculation
        s3.delete_object(org_id, project_id + "/" + doc_bin)
    s3.delete_object(org_id, project_id + "/" + prefixed_function_name)
    s3.delete_object(org_id, project_id + "/" + prefixed_payload)

    return calculated_attributes
