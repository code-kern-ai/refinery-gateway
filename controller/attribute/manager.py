from typing import List, Tuple, Dict, Any
from controller.tokenization.tokenization_service import (
    request_reupload_docbins,
)
import json
from submodules.model.business_objects import (
    attribute,
    record,
    project,
    tokenization,
    general,
)
from submodules.model.models import Attribute
from submodules.model.enums import (
    AttributeState,
    DataTypes,
    RecordTokenizationScope,
    AttributeVisibility,
)
from util import notification

from submodules.model import daemon
from submodules.s3 import controller as s3

from controller.task_master import manager as task_master_manager
from submodules.model.enums import TaskType
from . import util
from sqlalchemy import sql
from hashlib import md5

DEFAULT_LLM_RESPONSE_CONFIG = {
    "llmIdentifier": "Open AI",
    "templatePrompt": "Make your answer a single word, e.g. 'yes' or 'no'",
    "questionPrompt": "Is this clickbait? => '{{ headline }}'",
    "llmConfig": {
        "model": "gpt-4o-mini",
        "temperature": 0,
        "maxLength": 1024,
        "stopSequences": [],
        "topP": 1,
        "frequencyPenalty": 0,
        "presencePenalty": 0,
        "apiKey": None,
        "apiBase": None,
        "apiVersion": None,
    },
}


def get_attribute(project_id: str, attribute_id: str) -> Attribute:
    return attribute.get(project_id, attribute_id)


def get_all_attributes_by_names(
    project_id: str, attribute_names: List[str]
) -> List[Attribute]:
    return attribute.get_all_by_names(project_id, attribute_names)


def get_all_attributes(
    project_id: str, state_filter: List[str] = None
) -> List[Attribute]:
    if not state_filter:
        state_filter = [
            AttributeState.UPLOADED.value,
            AttributeState.USABLE.value,
            AttributeState.AUTOMATICALLY_CREATED.value,
        ]
    if len(state_filter) == 1 and state_filter[0].upper() == "ALL":
        state_filter = [e.value for e in AttributeState]
    return attribute.get_all_ordered(project_id, True, state_filter)


def check_composite_key(project_id: str) -> bool:
    return attribute.check_composite_key_is_valid(project_id)


def create_attribute(project_id: str, name: str) -> Attribute:
    prev_relative_position: int = attribute.get_relative_position(project_id)
    if prev_relative_position is None:
        relative_position = 1
    else:
        relative_position = prev_relative_position + 1

    attribute_item: Attribute = attribute.create(
        project_id,
        name,
        relative_position,
        with_commit=True,
    )
    return attribute_item


def create_user_attribute(project_id: str, name: str, data_type: str) -> Attribute:
    prev_relative_position: int = attribute.get_relative_position(project_id)
    if prev_relative_position is None:
        relative_position = 1
    else:
        relative_position = prev_relative_position + 1
    visibility = None  # default
    if data_type == DataTypes.EMBEDDING_LIST.value:
        visibility = AttributeVisibility.HIDE.value
    additional_config = None
    if data_type == DataTypes.LLM_RESPONSE.value:
        additional_config = DEFAULT_LLM_RESPONSE_CONFIG

    attribute_item: Attribute = attribute.create(
        project_id,
        name,
        relative_position,
        data_type=data_type,
        is_primary_key=False,
        user_created=True,
        state=AttributeState.INITIAL.value,
        visibility=visibility,
        with_commit=True,
        additional_config=additional_config,
    )
    notification.send_organization_update(
        project_id=project_id,
        message=f"calculate_attribute:created:{str(attribute_item.id)}",
    )

    return attribute_item


def update_attribute(
    project_id: str,
    attribute_id: str,
    data_type: str,
    is_primary_key: bool,
    name: str,
    source_code: str,
    visibility: str,
    additional_config: Dict[str, Any] = None,
) -> None:
    attribute_item: Attribute = attribute.update(
        project_id,
        attribute_id,
        data_type,
        is_primary_key,
        name,
        source_code,
        with_commit=True,
        visibility=visibility,
        additional_config=additional_config,
    )

    notification.send_organization_update(
        project_id=project_id,
        message=f"calculate_attribute:updated:{str(attribute_item.id)}",
    )


def delete_attribute(project_id: str, attribute_id: str) -> None:
    attribute_item = attribute.get(project_id, attribute_id)
    if attribute_item.user_created:
        is_text_attribute = (
            attribute_item.data_type == DataTypes.TEXT.value
            or attribute_item.data_type == DataTypes.LLM_RESPONSE.value
        )
        is_usable = attribute_item.state == AttributeState.USABLE.value
        if is_usable:
            record.delete_user_created_attribute(
                project_id=project_id, attribute_id=attribute_id, with_commit=True
            )
        elif not is_usable and attribute_item.data_type == DataTypes.LLM_RESPONSE.value:
            project_item = project.get(project_id)
            org_id = str(project_item.organization_id)
            s3.delete_object(org_id, project_id + "/" + f"{attribute_id}_knowledge")
            s3.delete_object(org_id, project_id + "/" + f"{attribute_id}_llm_ac_cache")

        attribute.delete(project_id, attribute_id, with_commit=True)
        if is_usable and not is_text_attribute:
            request_reupload_docbins(project_id)
        notification.send_organization_update(
            project_id=project_id, message=f"calculate_attribute:deleted:{attribute_id}"
        )
        if is_usable:
            notification.send_organization_update(
                project_id=project_id, message="attributes_updated"
            )
    else:
        raise ValueError("Attribute is not user created")


def add_running_id(
    user_id: str,
    org_id: str,
    project_id: str,
    attribute_name: str,
    for_retokenization: bool = True,
) -> None:
    if attribute.get_by_name(project_id, attribute_name):
        raise ValueError(f"attribute with name {attribute_name} already exists")
    general.commit()

    # added threading for session management because otherwise this can sometimes create a deadlock
    thread = daemon.prepare_thread(
        __add_running_id,
        user_id,
        org_id,
        project_id,
        attribute_name,
        for_retokenization,
    )
    thread.start()
    thread.join()


def __add_running_id(
    user_id: str,
    org_id: str,
    project_id: str,
    attribute_name: str,
    for_retokenization: bool = True,
):
    general.get_ctx_token()
    attribute.add_running_id(
        project_id, attribute_name, for_retokenization, with_commit=True
    )
    if for_retokenization:
        task_master_manager.queue_task(
            str(org_id),
            str(user_id),
            TaskType.TOKENIZATION,
            {
                "scope": RecordTokenizationScope.PROJECT.value,
                "include_rats": True,
                "only_uploaded_attributes": False,
                "project_id": str(project_id),
            },
        )
    general.remove_and_refresh_session()


def calculate_user_attribute_missing_records(
    project_id: str,
    org_id: str,
    user_id: str,
    attribute_id: str,
    include_rats: bool = True,
) -> None:
    if attribute.get_all(
        project_id=project_id, state_filter=[AttributeState.RUNNING.value]
    ):
        __notify_attribute_calculation_failed(
            project_id=project_id,
            attribute_id=attribute_id,
            log="Calculation of attribute failed. Another attribute is already running.",
            append_to_logs=False,
        )
        return

    if tokenization.get_doc_bin_progress(project_id):
        __notify_attribute_calculation_failed(
            project_id=project_id,
            attribute_id=attribute_id,
            log="Tokenization is not finished",
            append_to_logs=False,
        )
        return

    attribute_item = attribute.get(project_id, attribute_id)
    equally_named_attributes = attribute.get_all_by_names(
        project_id, [attribute_item.name]
    )
    usable_attributes = attribute.get_all(project_id)
    if len(set(equally_named_attributes) & set(usable_attributes)) > 1:
        __notify_attribute_calculation_failed(
            project_id=project_id,
            attribute_id=attribute_id,
            log="Calculation of attribute failed. Another attribute with the same name is already in state usable or uploaded.",
            append_to_logs=False,
        )
        return
    attribute.update(
        project_id=project_id,
        attribute_id=attribute_id,
        state=AttributeState.RUNNING.value,
        with_commit=True,
        started_at=sql.func.now(),
    )
    notification.send_organization_update(
        project_id=project_id, message=f"calculate_attribute:started:{attribute_id}"
    )
    daemon.run_without_db_token(
        __calculate_user_attribute_missing_records,
        project_id,
        org_id,
        user_id,
        attribute_id,
        include_rats,
    )


def __calculate_user_attribute_missing_records(
    project_id: str,
    org_id: str,
    user_id: str,
    attribute_id: str,
    include_rats: bool,
) -> None:
    general.get_ctx_token()

    all_records_count = record.count(project_id)
    count_delta = record.count_missing_delta(project_id, attribute_id)

    if count_delta != all_records_count:
        doc_bin = util.prepare_delta_records_doc_bin(
            attribute_id=attribute_id, project_id=project_id
        )
    else:
        doc_bin = "docbin_full"
    try:
        calculated_attributes = util.run_attribute_calculation_exec_env(
            attribute_id=attribute_id, project_id=project_id, doc_bin=doc_bin
        )
        if not calculated_attributes:
            __notify_attribute_calculation_failed(
                project_id=project_id,
                attribute_id=attribute_id,
                log="Calculation of attribute failed.",
            )
            return
    except Exception:
        __notify_attribute_calculation_failed(
            project_id=project_id,
            attribute_id=attribute_id,
            log="Attribute calculation failed",
        )
        general.remove_and_refresh_session()
        return

    util.add_log_to_attribute_logs(
        project_id, attribute_id, "Writing results to the database."
    )
    # add calculated attributes to database
    try:
        record.update_add_user_created_attribute(
            project_id=project_id,
            attribute_id=attribute_id,
            calculated_attributes=calculated_attributes,
            with_commit=True,
        )
    except Exception:
        record.delete_user_created_attribute(
            project_id=project_id,
            attribute_id=attribute_id,
            with_commit=True,
        )
        __notify_attribute_calculation_failed(
            project_id=project_id,
            attribute_id=attribute_id,
            log="Writing to the database failed.",
        )
        general.remove_and_refresh_session()
        return
    util.add_log_to_attribute_logs(project_id, attribute_id, "Finished writing.")

    attribute_item = attribute.get(project_id, attribute_id)
    if (
        attribute_item
        and (
            attribute_item.data_type == DataTypes.TEXT.value
            or attribute_item.data_type == DataTypes.LLM_RESPONSE.value
        )
        and not attribute_item.state == AttributeState.FAILED.value
    ):
        util.add_log_to_attribute_logs(
            project_id, attribute_id, "Triggering tokenization."
        )
        try:
            task_master_manager.queue_task(
                str(org_id),
                str(user_id),
                TaskType.TOKENIZATION,
                {
                    "scope": RecordTokenizationScope.ATTRIBUTE.value,
                    "attribute_id": str(attribute_item.id),
                    "include_rats": include_rats,
                    "project_id": str(project_id),
                },
            )

        except Exception:
            record.delete_user_created_attribute(
                project_id=project_id,
                attribute_id=attribute_id,
                with_commit=True,
            )
            __notify_attribute_calculation_failed(
                project_id=project_id,
                attribute_id=attribute_id,
                log="Writing to the database failed.",
            )
            general.remove_and_refresh_session()
            return

    else:
        util.add_log_to_attribute_logs(
            project_id, attribute_id, "Adding attribute to docbins."
        )
        request_reupload_docbins(project_id)

    attribute_item = attribute.get(project_id, attribute_id)
    if attribute_item.state == AttributeState.FAILED.value:
        __notify_attribute_calculation_failed(
            project_id=project_id,
            attribute_id=attribute_id,
            log="Writing to the database failed.",
        )
        general.remove_and_refresh_session()
        return
    util.set_progress(project_id, attribute_item, 1.0)
    attribute.update(
        project_id=project_id,
        attribute_id=attribute_id,
        state=AttributeState.USABLE.value,
        with_commit=True,
        finished_at=sql.func.now(),
    )

    notification.send_organization_update(
        project_id, f"calculate_attribute:finished:{attribute_id}"
    )
    general.remove_and_refresh_session()


def __notify_attribute_calculation_failed(
    project_id: str, attribute_id: str, log: str, append_to_logs: bool = True
) -> None:
    util.add_log_to_attribute_logs(project_id, attribute_id, log, append_to_logs)
    attribute.update(
        project_id=project_id,
        attribute_id=attribute_id,
        state=AttributeState.FAILED.value,
        with_commit=True,
    )
    notification.send_organization_update(
        project_id=project_id, message=f"calculate_attribute:error:{attribute_id}"
    )


def calculate_user_attribute_sample_records(
    project_id: str, attribute_id: str
) -> Tuple[List[str], List[str]]:
    doc_bin_samples = util.prepare_sample_records_doc_bin(
        attribute_id=attribute_id, project_id=project_id
    )
    calculated_attributes = util.run_attribute_calculation_exec_env(
        attribute_id=attribute_id,
        project_id=project_id,
        doc_bin=doc_bin_samples,
    )
    values = None
    if (
        attribute.get(project_id, attribute_id).data_type
        == DataTypes.EMBEDDING_LIST.value
    ):
        # values are json serialized so they can be easily transferred to the frontend.
        # Since the return type is a list of strings, without json.dumps a str(xxxx) will be called
        # which can't be easily deserialized if special characters are in the string
        values = [json.dumps(v) for v in list(calculated_attributes.values())]
    else:
        values = list(calculated_attributes.values())
    return list(calculated_attributes.keys()), values


def run_llm_playground(
    project_id: str,
    attribute_id: str,
    llm_playground_config: Dict[str, Any],
    record_ids: List[str],
):
    doc_bin_samples = util.prepare_sample_records_doc_bin(
        attribute_id=attribute_id, project_id=project_id, record_ids=record_ids
    )
    calculated_attributes = util.run_attribute_calculation_exec_env(
        attribute_id=attribute_id,
        project_id=project_id,
        doc_bin=doc_bin_samples,
        llm_playground_config=llm_playground_config,
    )
    return calculated_attributes


def llm_ac_cache(project_id: str, attribute_id: str):
    attribute_item = attribute.get(project_id, attribute_id)
    if attribute_item.data_type != DataTypes.LLM_RESPONSE.value:
        raise ValueError("Attribute is not an LLM response attribute")

    project_item = project.get(project_id)
    org_id = str(project_item.organization_id)

    llm_ac_cache_name = f"{attribute_id}_llm_ac_cache"
    num_total_records = record.get_count_all_records(project_id)

    if not s3.object_exists(org_id, project_id + "/" + llm_ac_cache_name):
        return {
            "num_cached_records": 0,
            "num_total_records": num_total_records,
            "has_cached_records": False,
        }

    llm_ac_cache = json.loads(
        s3.get_object(org_id, project_id + "/" + llm_ac_cache_name)
    )

    llm_config = {
        "client_type": attribute_item.additional_config["llmIdentifier"],
        "api_key": attribute_item.additional_config["llmConfig"]["apiKey"],
        "api_base": attribute_item.additional_config["llmConfig"]["apiBase"],
        "api_version": attribute_item.additional_config["llmConfig"]["apiVersion"],
        "model": attribute_item.additional_config["llmConfig"]["model"],
        "system_prompt": attribute_item.additional_config["templatePrompt"]
        + " You must only output valid JSON. If there is not yet a schema defined for the JSON output, please put everything into a single value under the key 'result' - otherwise stick to the schema that has been provided already.",
        "user_prompt": attribute_item.additional_config["questionPrompt"],
        "llm_kwargs": {
            "response_format": {"type": "json_object"},
            "stream": False,
            "stop": attribute_item.additional_config["llmConfig"]["stopSequences"],
            "temperature": float(
                attribute_item.additional_config["llmConfig"]["temperature"]
            ),
            "max_tokens": attribute_item.additional_config["llmConfig"]["maxLength"],
            "top_p": float(attribute_item.additional_config["llmConfig"]["topP"]),
            "frequency_penalty": float(
                attribute_item.additional_config["llmConfig"]["frequencyPenalty"]
            ),
            "presence_penalty": float(
                attribute_item.additional_config["llmConfig"]["presencePenalty"]
            ),
        },
    }

    llm_config_hash = md5(json.dumps(llm_config).encode()).hexdigest()
    cached_records = llm_ac_cache.get(llm_config_hash, {})
    return {
        "num_cached_records": len(cached_records),
        "num_total_records": num_total_records,
        "has_cached_records": bool(cached_records),
    }
