import time
from typing import Any, List
import uuid
import docker
import json
import os
import pytz

import datetime
from dateutil import parser

from submodules.model.business_objects import (
    attribute,
    general,
    record,
    project,
    tokenization,
)
from submodules.model.models import Attribute
from submodules.s3 import controller as s3
from util import daemon, notification
from controller.knowledge_base import util as knowledge_base
from submodules.model import enums

client = docker.from_env()
image = os.getenv("AC_EXEC_ENV_IMAGE")
exec_env_network = os.getenv("LF_NETWORK")
__tz = pytz.timezone("Europe/Berlin")

__containers_running = {}


def add_log_to_attribute_logs(
    project_id: str, attribute_id: str, log: str, append_to_logs: bool = True
) -> None:
    attribute_item = attribute.get(project_id, attribute_id)
    berlin_now = datetime.datetime.now(__tz)
    time_string = berlin_now.strftime("%Y-%m-%dT%H:%M:%S")
    line = f"{time_string} {log}"

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

    if attribute_item.logs:
        add_log_to_attribute_logs(
            project_id,
            attribute_id,
            "re-run attribute calculation",
            append_to_logs=False,
        )

    prefixed_function_name = f"{attribute_id}_fn"
    prefixed_payload = f"{attribute_id}_payload.json"
    prefixed_knowledge_base = f"{attribute_id}_knowledge"
    project_item = project.get(project_id)
    org_id = str(project_item.organization_id)

    s3.put_object(
        org_id,
        project_id + "/" + prefixed_function_name,
        attribute_item.source_code,
    )
    s3.put_object(
        org_id,
        project_id + "/" + prefixed_knowledge_base,
        knowledge_base.build_knowledge_base_from_project(project_id),
    )
    command = [
        s3.create_access_link(org_id, project_id + "/" + doc_bin),
        s3.create_access_link(org_id, project_id + "/" + prefixed_function_name),
        s3.create_access_link(org_id, project_id + "/" + prefixed_knowledge_base),
        project_item.tokenizer_blank,
        s3.create_file_upload_link(org_id, project_id + "/" + prefixed_payload),
        attribute_item.data_type,
    ]

    container_name = str(uuid.uuid4())
    container = client.containers.create(
        image=image,
        command=command,
        auto_remove=True,
        detach=True,
        network=exec_env_network,
    )
    set_progress(project_id, attribute_item, 0.05)
    __containers_running[container_name] = True
    daemon.run(
        read_container_logs_thread,
        project_id,
        container_name,
        str(attribute_item.id),
        container,
    )
    container.start()
    attribute_item.logs = [
        line.decode("utf-8").strip("\n")
        for line in container.logs(
            stream=True, stdout=True, stderr=True, timestamps=True
        )
        if "progress" not in line.decode("utf-8")
    ]
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
    set_progress(project_id, attribute_item, 0.9)

    return calculated_attributes


def extend_logs(
    project_id: str,
    attribute: Attribute,
    logs: List[str],
) -> None:
    if not logs or len(logs) == 0:
        return

    if not attribute.logs:
        attribute.logs = logs
    else:
        all_logs = [ll for ll in attribute.logs]
        all_logs += logs
        attribute.logs = all_logs
    general.commit()
    # currently dummy since frontend doesn't have a log change yet
    notification.send_organization_update(
        project_id, f"attributes_updated:{str(attribute.id)}"
    )


def read_container_logs_thread(
    project_id: str,
    name: str,
    attribute_id: str,
    docker_container: Any,
) -> None:
    ctx_token = general.get_ctx_token()
    # needs to be refetched since it is not thread safe
    attribute_item = attribute.get(project_id, attribute_id)
    previous_progress = -1
    last_timestamp = None
    c = 0
    while name in __containers_running:
        time.sleep(1)
        c += 1
        if c > 100:
            ctx_token = general.remove_and_refresh_session(ctx_token, True)
        attribute_item = attribute.get(project_id, attribute_id)
        if not attribute_item:
            break
        if attribute_item.state == enums.AttributeState.FAILED.value:
            break
        if name not in __containers_running:
            break
        try:
            # timestamps included to filter out logs that have already been read
            log_lines = docker_container.logs(
                stdout=True,
                stderr=True,
                timestamps=True,
                since=last_timestamp,
            )
        except Exception:
            # failsafe for containers that shut down during the read
            break
        current_logs = [
            ll
            for ll in str(log_lines.decode("utf-8")).split("\n")
            if len(ll.strip()) > 0
        ]
        if len(current_logs) == 0:
            continue
        last_entry = current_logs[-1]
        last_timestamp_str = last_entry.split(" ")[0]
        last_timestamp = parser.parse(last_timestamp_str).replace(
            tzinfo=None
        ) + datetime.timedelta(seconds=1)
        non_progress_logs = [ll for ll in current_logs if "progress" not in ll]
        progress_logs = [ll for ll in current_logs if "progress" in ll]
        if len(non_progress_logs) > 0:
            extend_logs(project_id, attribute_item, non_progress_logs)
        if len(progress_logs) == 0:
            continue
        last_entry = float(progress_logs[-1].split("progress: ")[1].strip())
        if previous_progress == last_entry:
            continue
        previous_progress = last_entry
        set_progress(project_id, attribute_item, last_entry * 0.8 + 0.05)
    general.remove_and_refresh_session(ctx_token)


def set_progress(
    project_id: str,
    attribute: Attribute,
    progress: float,
) -> None:
    final_progress = round(progress, 4)
    attribute.progress = final_progress
    general.commit()
    notification.send_organization_update(
        project_id, f"calculate_attribute:progress:{attribute.id}:{final_progress}"
    )
