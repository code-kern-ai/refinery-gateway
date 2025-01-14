import uuid

# import docker
import json

# import os

from submodules.model.business_objects import attribute, project, record
from submodules.s3 import controller as s3
from controller.attribute.util import (
    add_log_to_attribute_logs,
    set_progress,
)

# client = docker.from_env()
# image = os.getenv("AC_EXEC_ENV_IMAGE")
# exec_env_network = os.getenv("LF_NETWORK")

__containers_running = {}


def run_llm_attribute_calculation_exec_env(
    attribute_id: str, project_id: str, attribute_name: str
) -> None:
    attribute_item = attribute.get(project_id, attribute_id)
    project_item = project.get(project_id)
    record_items = record.get_attribute_data(project_id, attribute_name)
    org_id = str(project_item.organization_id)

    if not record_items:
        return

    if attribute_item.logs:
        add_log_to_attribute_logs(
            project_id,
            attribute_id,
            "re-run LLM attribute calculation",
            append_to_logs=False,
        )

    # prefixed_function_name = f"{attribute_id}_fn"
    prefixed_payload = f"{attribute_id}_payload.json"
    # prefixed_knowledge_base = f"{attribute_id}_knowledge"

    # s3.put_object(
    #     org_id,
    #     project_id + "/" + prefixed_function_name,
    #     attribute_item.source_code,
    # )
    # s3.put_object(
    #     org_id,
    #     project_id + "/" + prefixed_knowledge_base,
    #     knowledge_base.build_knowledge_base_from_project(project_id),
    # )
    # command = [
    #     s3.create_access_link(org_id, project_id + "/" + doc_bin),
    #     s3.create_access_link(org_id, project_id + "/" + prefixed_function_name),
    #     s3.create_access_link(org_id, project_id + "/" + prefixed_knowledge_base),
    #     project_item.tokenizer_blank,
    #     s3.create_file_upload_link(org_id, project_id + "/" + prefixed_payload),
    #     attribute_item.data_type,
    # ]

    container_name = str(uuid.uuid4())
    # container = client.containers.create(
    #     image=image,
    #     command=command,
    #     auto_remove=True,
    #     detach=True,
    #     network=exec_env_network,
    # )
    set_progress(project_id, attribute_item, 0.05)
    __containers_running[container_name] = True
    # daemon.run_without_db_token(
    #     read_container_logs_thread,
    #     project_id,
    #     container_name,
    #     str(attribute_item.id),
    #     container,
    # )
    # container.start()
    attribute_item.logs = []
    # attribute_item.logs = [
    #     line.decode("utf-8").strip("\n")
    #     for line in container.logs(
    #         stream=True, stdout=True, stderr=True, timestamps=True
    #     )
    #     if "progress" not in line.decode("utf-8")
    # ]
    del __containers_running[container_name]

    try:
        payload = s3.get_object(org_id, project_id + "/" + prefixed_payload)
        calculated_attributes = json.loads(payload)
    except Exception:
        print("Could not grab data from s3 -- attribute calculation")
        calculated_attributes = {}

    # if not doc_bin == "docbin_full":
    #     # sample records docbin should be deleted after calculation
    #     s3.delete_object(org_id, project_id + "/" + doc_bin)
    # s3.delete_object(org_id, project_id + "/" + prefixed_function_name)
    # s3.delete_object(org_id, project_id + "/" + prefixed_payload)
    set_progress(project_id, attribute_item, 0.9)

    return calculated_attributes


def run_llm_attribute_calculation_sample_records(
    attribute_id: str, project_id: str, attribute_name: str, limit: int = 10
) -> None:
    attribute_item = attribute.get(project_id, attribute_id)
    project_item = project.get(project_id)
    record_items = record.get_sample_data_of(
        project_item.project_id, attribute_name, limit
    )
    # org_id = str(project_item.organization_id)

    if not record_items:
        return

    if attribute_item.logs:
        add_log_to_attribute_logs(
            project_id,
            attribute_id,
            "re-run sample LLM attribute calculation",
            append_to_logs=False,
        )
