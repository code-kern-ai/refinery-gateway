import time
from typing import Any, List
import uuid
import docker
import json
import os
import pytz
import re
from datetime import datetime
from submodules.model.business_objects import attribute, general, record, project, tokenization
from submodules.model.enums import DataTypes
from submodules.model.models import Attribute
from submodules.s3 import controller as s3
from util import daemon, notification

client = docker.from_env()
image = os.getenv("AC_EXEC_ENV_IMAGE")
exec_env_network = os.getenv("LF_NETWORK")
__tz = pytz.timezone("Europe/Berlin")

__containers_running = {}

def add_log_to_attribute_logs(
    project_id: str, attribute_id: str, log: str, append_to_logs: bool = True
) -> None:
    attribute_item = attribute.get(project_id, attribute_id)
    berlin_now = datetime.now(__tz)
    time_string = berlin_now.strftime("%Y-%m-%dT%H:%M:%S")
    line = f"{time_string} {log}"
    line = log

    if not append_to_logs or not attribute_item.logs:
        logs = [line]
        attribute.update(
            project_id=project_id,
            attribute_id=attribute_id,
            logs=logs,
            with_commit=True,
        )
    else:
        attribute_item.logs.append(line)
        general.commit()

def extend_attribute_logs(
    project_id: str, attribute_id: str, logs: List[str]
) -> None:
    attribute_item = attribute.get(project_id, attribute_id)
    if not attribute_item.logs:
        attribute_item.logs = []

    berlin_now = datetime.now(__tz)
    time_string = berlin_now.strftime("%Y-%m-%dT%H:%M:%S")
    logs = [f"{time_string} {line}" for line in logs]

    attribute_item.logs.extend(logs)
    general.commit()

def prepare_sample_records_doc_bin(attribute_id: str, project_id: str) -> str:
    sample_records = record.get_attribute_calculation_sample_records(project_id)

    sample_records_doc_bin = tokenization.get_doc_bin_table_to_json(
        project_id=project_id,
        missing_columns=record.get_missing_columns_str(project_id),
        record_ids=[r[0] for r in sample_records],
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
        attribute_item.data_type,
    ]

    # initial log preparation
    update_progress(project_id=project_id, attribute_item=attribute_item, progress=0.05)

    container_name = str(uuid.uuid4())
    container = client.containers.create(
        image=image,
        command=command,
        auto_remove=True,
        detach=True,
        network=exec_env_network,
    )
    __containers_running[container_name] = True
    daemon.run(__read_container_logs_thread, project_id, container_name, attribute_id, container)
    container.start()
    logs = [
        line.decode("utf-8").strip("\n")
        for line in container.logs(
            stream=True, stdout=True, stderr=True
        )
        if "progress" not in line.decode("utf-8")
    ]

    logs = extend_attribute_logs(project_id, attribute_id, logs)
    del __containers_running[container_name]

    try:
        payload = s3.get_object(org_id, project_id + "/" + prefixed_payload)
        calculated_attributes = json.loads(payload)
    except Exception:
        print("Could not grab data from s3 -- attribute calculation")
        calculated_attributes = {}

    if not doc_bin == "docbin_full":
        # sample records docbin should be deleted after calculation
        s3.delete_object(org_id, project_id + "/" + doc_bin)
    s3.delete_object(org_id, project_id + "/" + prefixed_function_name)
    s3.delete_object(org_id, project_id + "/" + prefixed_payload)

    return calculated_attributes


def __read_container_logs_thread(
    project_id: str,
    container_name: str,
    attribute_id: str,
    docker_container: Any,
) -> None:

    ctx_token = general.get_ctx_token()

    attribute_item = attribute.get(project_id, attribute_id)
    c = 0
    while container_name in __containers_running:
        time.sleep(1)
        c += 1
        if c > 100:
            ctx_token = general.remove_and_refresh_session(ctx_token, True)
            attribute_item = attribute.get(project_id, attribute_id)
        if not container_name in __containers_running:
            break
        try:
            last_progress = 0.05
            for log in docker_container.logs(
                stream=True,
                tail=25
            ):
                line = log.decode("utf-8")
                if "progress:" in line:
                    value = line.split(":")[-1].strip()
                    progress = float(value)
                    if progress > 0.95:
                        progress = 0.95
                    if progress > last_progress:
                        last_progress = progress
                        update_progress(project_id, attribute_item, progress)
        except Exception:
            continue
    general.remove_and_refresh_session(ctx_token)


def update_progress(project_id: str, attribute_item: Attribute, progress: float) -> None:
    print("progress", progress, flush=True)
    attribute_item.progress = progress
    general.commit()
    message = f"calculate_attribute:progress:{attribute_item.id}:{progress}"
    notification.send_organization_update(project_id, message)
    