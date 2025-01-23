import sys
import time
from typing import Union, Any, List, Dict
import uuid
import docker
import json
import os
import pytz
import traceback
import requests
import re

import datetime
from dateutil import parser

from exceptions.exceptions import LlmResponseError
from submodules.model.business_objects import (
    attribute,
    general,
    record,
    project,
    tokenization,
)
from submodules.model.models import Attribute
from submodules.s3 import controller as s3
from util import notification
from controller.knowledge_base import util as knowledge_base
from submodules.model import enums
from submodules.model import daemon

client = docker.from_env()
image = os.getenv("AC_EXEC_ENV_IMAGE")
exec_env_network = os.getenv("LF_NETWORK")
__tz = pytz.timezone("Europe/Berlin")

__containers_running = {}

LLM_RESPONSE_TMPL_PATH = "controller/attribute/llm_response_tmpl.py"


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


def prepare_sample_records_doc_bin(
    attribute_id: str, project_id: str, record_ids: Union[List[str], None] = None
) -> str:
    sample_records = record.get_attribute_calculation_sample_records(project_id)

    sample_records_doc_bin = tokenization.get_doc_bin_table_to_json(
        project_id=project_id,
        missing_columns=record.get_missing_columns_str(project_id),
        record_ids=record_ids or [r[0] for r in sample_records],
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


def test_openai_llm_connection(api_key: str, model: str):
    # more here: https://platform.openai.com/docs/api-reference/making-requests
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": "only say 'hello'"}]},
        ],
        "max_tokens": 20,
    }

    response = requests.post(
        "https://api.openai.com/v1/chat/completions", headers=headers, json=payload
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def test_azure_llm_connection(
    api_key: str, base_endpoint: str, api_version: str, model: str
):
    # more here: https://learn.microsoft.com/en-us/azure/ai-services/openai/reference-preview
    base_endpoint = base_endpoint.rstrip("/")
    api_version_parts = (
        api_version.split("-")
        if "preview" not in api_version
        else api_version.replace("-preview", "").split("-")
    )
    assert (
        len(api_version_parts) == 3
        and len(api_version_parts[0]) == 4
        and len(api_version_parts[1]) == 2
        and len(api_version_parts[2]) == 2
    )

    final_endpoint = f"{base_endpoint}/openai/deployments/{model}/chat/completions?api-version={api_version}"
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key,
    }

    payload = {
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": "only say 'hello'"}]},
        ],
        "max_tokens": 20,
    }

    response = requests.post(final_endpoint, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def validate_user_prompt(project_id: str, user_prompt: str):
    def parse_mustache_attribute_names(mustache_str: str) -> List[str]:
        for brace in "{}":
            mustache_str = mustache_str.replace(brace, "")
        return mustache_str.strip()

    mustache_attributes = list(
        map(
            parse_mustache_attribute_names,
            re.findall(r"{{\s*[A-Za-z0-9_]+\s*}}", user_prompt),
        )
    )

    # 5 as min len criterion for double curly brackets + single char attribute
    if len(user_prompt) < 5 or len(mustache_attributes) == 0:
        raise LlmResponseError(
            "User prompt does not carry a single valid Mustache syntax for attribute access. "
            "You can access attributes by using '{{ attribute_name }}' in your prompt."
        )

    for attr in mustache_attributes:
        if not attribute.get_by_name(project_id, attr):
            raise LlmResponseError(f"Attribute '{attr}' does not exist in the project.")


def validate_llm_config(llm_config: Dict[str, Any]):
    # test LLM connection before sending work package to execution environment
    try:
        if llm_config["llmIdentifier"] == enums.LLMProvider.OPENAI.value:
            test_openai_llm_connection(
                api_key=llm_config["apiKey"],
                model=llm_config["model"],
            )
        elif llm_config["llmIdentifier"] == enums.LLMProvider.AZURE.value:
            test_azure_llm_connection(
                api_key=llm_config["apiKey"],
                model=llm_config["model"],
                base_endpoint=llm_config["apiBase"],
                api_version=llm_config["apiVersion"],
            )
        else:
            raise LlmResponseError(
                "LLM Identifier must be either Open AI or Azure, got: "
                + llm_config["llmIdentifier"]
            )
    except AssertionError:
        raise LlmResponseError(
            "API version format must be YYYY-MM-DD, got: " + llm_config["apiVersion"]
        )
    except requests.exceptions.RequestException:
        raise LlmResponseError(
            "Encountered Exception when trying LLM connection: "
            + traceback.format_exception(*sys.exc_info())[-1]
        )


def prepare_llm_response_code(
    attribute_item: Attribute, llm_playground_config: Union[Dict[str, Any], None] = None
) -> str:
    global LLM_RESPONSE_TMPL_PATH
    with open(LLM_RESPONSE_TMPL_PATH, "r") as file:
        lines = [line.rstrip() for line in file if line[0] != "#"]

    llm_code = "\n".join(lines)
    source_code = attribute_item.source_code

    # llm_playground_config is only set if `run-llm-playground`` invoked this function
    if not attribute_item.additional_config and llm_playground_config is None:
        llm_config = {}
    elif llm_playground_config is None:
        llm_config = dict(
            attribute_item.additional_config.get("llmConfig", {}),
            llmIdentifier=attribute_item.additional_config["llmIdentifier"],
            templatePrompt=attribute_item.additional_config["templatePrompt"],
            questionPrompt=attribute_item.additional_config["questionPrompt"],
        )
    else:
        source_code = """import json

def ac(record):
    llm_response = get_llm_response()
    return json.dumps(llm_response, indent=2)"""

        llm_config = dict(
            llm_playground_config.get("llmConfig", {}),
            llmIdentifier=llm_playground_config["llmIdentifier"],
            templatePrompt=llm_playground_config["templatePrompt"],
            questionPrompt=llm_playground_config["questionPrompt"],
        )
    # already raises expressive LlmResponseError
    validate_user_prompt(
        project_id=attribute_item.project_id,
        user_prompt=llm_config["questionPrompt"],
    )
    validate_llm_config(llm_config=llm_config)

    try:
        llm_config_mapping = {
            "@@API_KEY@@": llm_config["apiKey"],
            "@@API_BASE@@": llm_config.get("apiBase") or "",
            "@@API_VERSION@@": llm_config.get("apiVersion") or "",
            "@@MODEL@@": llm_config["model"],
            "@@STOP_SEQUENCE@@": json.dumps(llm_config.get("stopSequences", [])),
            "@@TEMPERATURE@@": str(llm_config.get("temperature", 0)),
            "@@MAX_TOKENS@@": str(llm_config.get("maxLength", 1024)),
            "@@TOP_P@@": str(llm_config.get("topP", 1)),
            "@@FREQUENCY_PENALTY@@": str(llm_config.get("frequencyPenalty", 0)),
            "@@PRESENCE_PENALTY@@": str(llm_config.get("presencePenalty", 0)),
            "@@CLIENT_TYPE@@": llm_config["llmIdentifier"],
            "@@SYSTEM_PROMPT@@": llm_config["templatePrompt"].replace('"', "'"),
            "@@USER_PROMPT@@": llm_config["questionPrompt"].replace('"', "'"),
        }
    except KeyError:
        raise LlmResponseError(
            "LLM configuration is missing a required field: "
            + traceback.format_exception(*sys.exc_info())[-1]
        )

    for key, value in llm_config_mapping.items():
        llm_code = llm_code.replace(key, value)

    final_code = llm_code + "\n\n" + source_code

    return final_code  # this still has mustache templates in it (e.g. in user_prompt)


def run_attribute_calculation_exec_env(
    attribute_id: str,
    project_id: str,
    doc_bin: str,
    llm_playground_config: Union[Dict[str, Any], None] = None,
) -> None:
    attribute_item = attribute.get(project_id, attribute_id)

    if attribute_item.logs and llm_playground_config is None:
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

    source_code = attribute_item.source_code
    if attribute_item.data_type == enums.DataTypes.LLM_RESPONSE.value:
        try:
            source_code = prepare_llm_response_code(
                attribute_item, llm_playground_config=llm_playground_config
            )
        except LlmResponseError as e:
            error_message = e.args[0]
            if llm_playground_config is None:
                add_log_to_attribute_logs(
                    attribute_item.project_id,
                    attribute_item.id,
                    error_message,
                    append_to_logs=False,
                )
                return {}
            else:
                return {"logs": [error_message]}

    s3.put_object(
        org_id,
        project_id + "/" + prefixed_function_name,
        source_code,
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
    if llm_playground_config is None:
        set_progress(project_id, attribute_item, 0.05)
    __containers_running[container_name] = True
    if llm_playground_config is None:
        daemon.run_without_db_token(
            read_container_logs_thread,
            project_id,
            container_name,
            str(attribute_item.id),
            container,
        )
    container.start()
    final_logs = [
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
    if llm_playground_config is None:
        attribute_item.logs = final_logs
        set_progress(project_id, attribute_item, 0.9)
        return calculated_attributes
    return {**calculated_attributes, "logs": final_logs}


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
