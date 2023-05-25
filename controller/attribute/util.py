from dateutil import parser
import time
from typing import Any, List
import uuid
import docker
import json
import os
import pytz
import re
from datetime import datetime, timedelta
from submodules.model.business_objects import attribute, general, record, project, tokenization
from submodules.model.enums import DataTypes
from submodules.model.models import Attribute
from submodules.s3 import controller as s3
from util import daemon, notification

client = docker.from_env()
image = os.getenv("AC_EXEC_ENV_IMAGE")
exec_env_network = os.getenv("LF_NETWORK")

__containers_running = {}

def add_log_to_attribute_logs(
    project_id: str, attribute_id: str, log: str, append_to_logs: bool = True
) -> None:
    attribute_item = attribute.get(project_id, attribute_id)
    berlin_now = datetime.now(pytz.timezone("Europe/Berlin"))
    if append_to_logs:
        logs = attribute_item.logs
        if not logs:
            attribute_item.logs = []
            logs = attribute_item.logs
        logs.append(" ".join([berlin_now.strftime("%Y-%m-%dT%H:%M:%S"), log]))
    else:
        logs = [" ".join([berlin_now.strftime("%Y-%m-%dT%H:%M:%S"), log])]
    attribute.update(
        project_id=project_id,
        attribute_id=attribute_id,
        logs=logs,
        with_commit=True,
    )


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
    __update_progress(project_id=project_id, attribute_item=attribute_item, progress=0.0)

    container_name = str(uuid.uuid4())
    container = client.containers.create(
        image=image,
        command=command,
        remove=True,
        detach=True,
        network=exec_env_network,
    )
    __containers_running[container_name] = True
    daemon.run(__read_container_logs_thread, project_id, container_name, attribute_id, container)
    container.start()

    # final log preparation
    logs = [
        line.decode("utf-8").strip("\n")
        for line in container.logs(
            stream=True, stdout=True, stderr=True, timestamps=True
        )
        if "progress" not in line.decode("utf-8")
    ]

    del __containers_running[container_name]
    __update_progress(project_id, attribute_item, 1.0) 

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
):

    ctx_token = general.get_ctx_token()
    # needs to be refetched since it is not thread safe
    attribute_item = attribute.get(project_id, attribute_id)
    previous_progress = -1
    last_timestamp = None
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
            log_lines = docker_container.logs(
                stdout=True,
                stderr=True,
                timestamps=True,
                since=last_timestamp,
            )
        except:
            # failsafe for containers that shut down during the read
            break
        current_logs = [
            l for l in str(log_lines.decode("utf-8")).split("\n") if len(l.strip()) > 0
        ]

        if len(current_logs) == 0:
            continue
        last_entry = current_logs[-1]
        last_timestamp_str = last_entry.split(" ")[0]
        last_timestamp = parser.parse(last_timestamp_str).replace(
            tzinfo=None
        ) + timedelta(seconds=1)
        progress_logs = [l for l in current_logs if "progress" in l]
        if len(progress_logs) == 0:
            continue
        progress = float(progress_logs[-1].split(":")[-1].strip())
        if previous_progress == last_entry:
            continue
        previous_progress = last_entry
        __update_progress(
            project_id, attribute_item, progress
        )
    general.remove_and_refresh_session(ctx_token)


def __update_logs(
    project_id: str,
    attribute_item: Attribute,
    logs: List[str],
    ) -> None:
    if not logs or len(logs) == 0:
        return

    if not attribute_item.logs:
        attribute_item.logs = logs
    else:
        all_logs = [l for l in attribute_item.logs]
        all_logs += logs
        attribute_item.logs = all_logs
    general.commit()
    # currently dummy since frontend doesn't have a log change yet
    message = f"calculate_attribute:logs:{attribute_item.id}"
    notification.send_organization_update(project_id, message)

def __update_progress(project_id: str, attribute_item: Attribute, progress: float) -> None:
    attribute_item.progress = progress
    general.commit()
    message = f"calculate_attribute:progress:{attribute_item.id}:{progress}"
    notification.send_organization_update(project_id, message)
    