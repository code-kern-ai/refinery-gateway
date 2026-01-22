import json
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import sql

from submodules.s3 import controller as s3
from submodules.model import daemon
from submodules.model.models import DataBlockAttribute
from submodules.model.enums import AttributeState, DataTypes
from submodules.model.exceptions import EntityNotFoundException
from submodules.model.business_objects import (
    general,
    project as project_db_bo,
    data_block as data_block_db_bo,
    data_block_attributes as data_block_attributes_db_bo,
)
from controller.data_block import (
    manager as data_block_manager,
    util as data_block_util,
)
from controller.attribute import (
    util as attribute_util,
)
from util import notification

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


def get(data_block_id: str, attribute_id: str) -> DataBlockAttribute:
    attribute = data_block_attributes_db_bo.get(data_block_id, attribute_id)
    if attribute_id and not attribute:
        raise EntityNotFoundException
    return attribute


def get_all(
    data_block_id: str,
    state_filter: Optional[List[str]] = None,
) -> List[DataBlockAttribute]:
    return data_block_attributes_db_bo.get_all(data_block_id, state_filter)


def get_by_name(data_block_id: str, name: str) -> DataBlockAttribute:
    return data_block_attributes_db_bo.get_by_name(data_block_id, name)


def get_schema(data_block_id: str) -> List[Dict[str, str]]:
    return data_block_attributes_db_bo.get_schema_as_list(data_block_id)


def create(
    data_block_id: str,
    name: str,
    data_type: str = DataTypes.TEXT.value,
    user_created: bool = False,
    relative_position: Optional[int] = None,
    source_code: Optional[str] = "",
    state: Optional[str] = None,
    additional_config: Optional[Dict[str, Any]] = None,
) -> DataBlockAttribute:
    # Check if attribute with same name already exists
    existing = data_block_attributes_db_bo.get_by_name(data_block_id, name)
    if existing:
        raise ValueError(
            f"Attribute with name '{name}' already exists for this data block"
        )

    if data_type == DataTypes.LLM_RESPONSE.value:
        additional_config = additional_config or DEFAULT_LLM_RESPONSE_CONFIG

    return data_block_attributes_db_bo.create(
        data_block_id=data_block_id,
        name=name,
        data_type=data_type,
        relative_position=(
            relative_position
            or data_block_attributes_db_bo.get_max_relative_position(data_block_id) + 1
        ),
        user_created=user_created,
        source_code=source_code,
        state=state or AttributeState.INITIAL.value,
        additional_config=additional_config,
        with_commit=True,
    )


def create_many(
    data_block_id: str,
    attributes: List[Dict[str, Any]],
) -> List[DataBlockAttribute]:
    """
    Create multiple attributes at once.
    Each attribute dict should contain: name, data_type, and optionally state.
    """
    return data_block_attributes_db_bo.create_many(
        data_block_id=data_block_id,
        attributes=attributes,
        with_commit=True,
    )


def update(
    data_block_id: str,
    attribute_id: str,
    name: Optional[str] = None,
    data_type: Optional[str] = None,
    relative_position: Optional[int] = None,
    source_code: Optional[str] = None,
    state: Optional[str] = None,
    logs: Optional[List[str]] = None,
    progress: Optional[float] = None,
    additional_config: Optional[Dict[str, Any]] = None,
) -> DataBlockAttribute:
    attribute = data_block_attributes_db_bo.get(data_block_id, attribute_id)
    if not attribute:
        raise EntityNotFoundException

    return data_block_attributes_db_bo.update(
        data_block_id=data_block_id,
        attribute_id=attribute_id,
        name=name,
        data_type=data_type,
        relative_position=relative_position,
        source_code=source_code,
        state=state,
        logs=logs,
        progress=progress,
        additional_config=additional_config,
        with_commit=True,
    )


def delete_many(data_block_id: str, attribute_ids: Optional[List[str]] = None) -> None:
    data_block = data_block_db_bo.get_by_id(data_block_id)
    if not attribute_ids:
        attribute_ids = data_block_attributes_db_bo.get_all(
            data_block_id=data_block_id,
            # TODO: confirm if both states are needed
            state_filter=[AttributeState.INITIAL.value, AttributeState.USABLE.value],
        )
    for attribute_id in attribute_ids:
        attribute_item = data_block_attributes_db_bo.get(data_block_id, attribute_id)
        if attribute_item.user_created:
            # is_text_attribute = (
            #     attribute_item.data_type == DataTypes.TEXT.value
            #     or attribute_item.data_type == DataTypes.LLM_RESPONSE.value
            # )
            project_item = project_db_bo.get(data_block.project_id)
            org_id = str(project_item.organization_id)
            is_usable = attribute_item.state == AttributeState.USABLE.value
            if is_usable:
                data_block_manager.delete_user_created_attribute(
                    data_block_id=data_block_id,
                    attribute_id=attribute_id,
                    with_commit=True,
                )
            elif (
                not is_usable
                and attribute_item.data_type == DataTypes.LLM_RESPONSE.value
            ):
                s3.delete_object(
                    org_id,
                    str(project_item.id)
                    + "/data-blocks/"
                    + f"{attribute_id}_llm_ac_cache",
                )
                s3.delete_object(
                    org_id,
                    str(project_item.id)
                    + "/data-blocks/"
                    + f"{attribute_id}_knowledge",
                )

            data_block_attributes_db_bo.delete(
                data_block_id, attribute_id, with_commit=True
            )
            # NOTE: docbin_full gets re-uploaded on each execute_query call
            # if is_usable and not is_text_attribute:
            #     request_reupload_docbins(project_id)
            notification.send_organization_update(
                project_id=data_block.project_id,
                message=f"calculate_attribute:deleted:{attribute_id}",
            )
            if is_usable:
                notification.send_organization_update(
                    project_id=data_block.project_id, message="attributes_updated"
                )
        else:
            raise ValueError("Attribute is not user created")


def sync_schema(
    data_block_id: str,
    schema: List[Dict[str, str]],
) -> List[DataBlockAttribute]:
    """
    Synchronize attributes from a schema definition.
    This replaces the old sql_schema column functionality.

    Args:
        data_block_id: The ID of the data block
        schema: List of dicts with column_name, column_data_type, and optionally state

    Returns:
        List of created/updated DataBlockAttribute
    """
    return data_block_attributes_db_bo.sync_attributes_from_schema(
        data_block_id=data_block_id,
        schema=schema,
        with_commit=True,
    )


def calculate_data_block_attribute_records(
    project_id: str,
    data_block_id: str,
    attribute_id: str,
) -> Tuple[List[str], List[Any]]:
    if data_block_attributes_db_bo.get_all(
        data_block_id=data_block_id, state_filter=[AttributeState.RUNNING.value]
    ):
        __notify_attribute_calculation_failed(
            project_id=project_id,
            data_block_id=data_block_id,
            attribute_id=attribute_id,
            log="Calculation of attribute failed. Another attribute is already running.",
            append_to_logs=False,
        )
        return

    attribute_item = data_block_attributes_db_bo.get(data_block_id, attribute_id)
    equally_named_attributes = data_block_attributes_db_bo.get_all_by_names(
        data_block_id, [attribute_item.name]
    )
    usable_attributes = data_block_attributes_db_bo.get_all(data_block_id)
    if len(set(equally_named_attributes) & set(usable_attributes)) > 1:
        __notify_attribute_calculation_failed(
            project_id=project_id,
            data_block_id=data_block_id,
            attribute_id=attribute_id,
            log="Calculation of attribute failed. Another attribute with the same name is already in state usable or uploaded.",
            append_to_logs=False,
        )
        return
    data_block_attributes_db_bo.update(
        data_block_id=data_block_id,
        attribute_id=attribute_id,
        state=AttributeState.RUNNING.value,
        with_commit=True,
        started_at=sql.func.now(),
    )
    notification.send_organization_update(
        project_id=project_id, message=f"calculate_attribute:started:{attribute_id}"
    )
    daemon.run_without_db_token(
        __calculate_data_block_attribute_records,
        project_id,
        data_block_id,
        attribute_id,
    )


def __calculate_data_block_attribute_records(
    project_id: str,
    data_block_id: str,
    attribute_id: str,
) -> None:
    general.get_ctx_token()

    doc_bin = "docbin_full"
    data_block_util.prepare_records(
        data_block_id, attribute_id=attribute_id, prefix=doc_bin
    )
    try:
        calculated_attributes = attribute_util.run_attribute_calculation_exec_env(
            attribute_id=attribute_id,
            project_id=project_id,
            doc_bin=doc_bin,
            data_block_id=data_block_id,
            data_block_attribute_id=attribute_id,
        )
        if not calculated_attributes:
            __notify_attribute_calculation_failed(
                project_id=project_id,
                data_block_id=data_block_id,
                attribute_id=attribute_id,
                log="Calculation of attribute failed.",
            )
            return
    except Exception as e:
        __notify_attribute_calculation_failed(
            project_id=project_id,
            data_block_id=data_block_id,
            attribute_id=attribute_id,
            log=f"Attribute calculation failed: {str(e)}",
        )
        general.remove_and_refresh_session()
        return

    attribute_util.add_log_to_attribute_logs(
        project_id,
        None,
        "Writing results to the database.",
        data_block_attribute_id=attribute_id,
        data_block_id=data_block_id,
    )
    # add calculated attributes to database
    try:
        data_block_manager.update_add_user_created_attribute(
            data_block_id=data_block_id,
            attribute_id=attribute_id,
            calculated_attributes=calculated_attributes,
            with_commit=True,
        )
    except Exception:
        data_block_manager.delete_user_created_attribute(
            data_block_id=data_block_id,
            attribute_id=attribute_id,
            with_commit=True,
        )
        __notify_attribute_calculation_failed(
            project_id=project_id,
            data_block_id=data_block_id,
            attribute_id=attribute_id,
            log="Writing to the database failed.",
        )
        general.remove_and_refresh_session()
        return

    attribute_util.add_log_to_attribute_logs(
        project_id,
        None,
        "Finished writing.",
        data_block_attribute_id=attribute_id,
        data_block_id=data_block_id,
    )
    # attribute_item = data_block_attributes_db_bo.get(data_block_id, attribute_id)
    # if (
    #     attribute_item
    #     and (
    #         attribute_item.data_type == DataTypes.TEXT.value
    #         or attribute_item.data_type == DataTypes.LLM_RESPONSE.value
    #     )
    #     and not attribute_item.state == AttributeState.FAILED.value
    # ):
    #     util.add_log_to_attribute_logs(
    #         project_id, attribute_id, "Triggering tokenization."
    #     )
    #     try:
    #         task_master_manager.queue_task(
    #             str(org_id),
    #             str(user_id),
    #             TaskType.TOKENIZATION,
    #             {
    #                 "scope": RecordTokenizationScope.ATTRIBUTE.value,
    #                 "attribute_id": str(attribute_item.id),
    #                 "include_rats": include_rats,
    #                 "project_id": str(project_id),
    #             },
    #         )

    #     except Exception:
    #         record.delete_user_created_attribute(
    #             project_id=project_id,
    #             attribute_id=attribute_id,
    #             with_commit=True,
    #         )
    #         __notify_attribute_calculation_failed(
    #             project_id=project_id,
    #             attribute_id=attribute_id,
    #             log="Writing to the database failed.",
    #         )
    #         general.remove_and_refresh_session()
    #         return

    # else:
    #     util.add_log_to_attribute_logs(
    #         project_id, attribute_id, "Adding attribute to docbins."
    #     )
    #     request_reupload_docbins(project_id)

    attribute_item = data_block_attributes_db_bo.get(data_block_id, attribute_id)
    if attribute_item.state == AttributeState.FAILED.value:
        __notify_attribute_calculation_failed(
            project_id=project_id,
            data_block_id=data_block_id,
            attribute_id=attribute_id,
            log="Writing to the database failed.",
        )
        general.remove_and_refresh_session()
        return
    attribute_util.set_progress(project_id, attribute_item, 1.0)
    data_block_attributes_db_bo.update(
        data_block_id=data_block_id,
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
    project_id: str,
    data_block_id: str,
    attribute_id: str,
    log: str,
    append_to_logs: bool = True,
) -> None:
    attribute_util.add_log_to_attribute_logs(
        project_id, None, log, append_to_logs, attribute_id, data_block_id
    )
    data_block_attributes_db_bo.update(
        data_block_id=data_block_id,
        attribute_id=attribute_id,
        state=AttributeState.FAILED.value,
        with_commit=True,
    )
    notification.send_organization_update(
        project_id=project_id, message=f"calculate_attribute:error:{attribute_id}"
    )


def calculate_sample_records(
    org_id: str,
    data_block_id: str,
    attribute_id: str,
    limit: int = 10,
) -> Tuple[List[str], List[Any]]:
    # Get data block for project_id
    data_block = data_block_db_bo.get(org_id, data_block_id)
    if not data_block:
        raise EntityNotFoundException(f"Data block {data_block_id} not found")

    project_id = str(data_block.project_id)

    # Prepare doc_bin from DataBlockResults
    sample_records_prefix = data_block_util.prepare_records(
        data_block_id=data_block_id, attribute_id=attribute_id, limit=limit
    )

    # Run calculation using shared execution environment
    calculated_attributes = attribute_util.run_attribute_calculation_exec_env(
        attribute_id=None,
        project_id=project_id,
        data_block_id=data_block_id,
        data_block_attribute_id=attribute_id,
        doc_bin=sample_records_prefix,
    )

    # Get attribute for data type
    attribute = data_block_attributes_db_bo.get(data_block_id, attribute_id)
    if attribute.data_type in (
        DataTypes.EMBEDDING_LIST.value,
        DataTypes.TEXT_LIST.value,
    ):
        # JSON serialize list values for frontend transfer
        values = [json.dumps(v) for v in calculated_attributes.values()]
    else:
        values = list(calculated_attributes.values())

    return list(calculated_attributes.keys()), values


def run_llm_playground(
    data_block_id: str,
    attribute_id: str,
    llm_playground_config: Dict[str, Any],
    record_indices: List[int],
) -> Dict[str, Any]:
    data_block = data_block_db_bo.get_by_id(data_block_id)
    if not data_block:
        raise EntityNotFoundException(f"Data block {data_block_id} not found")

    project_id = str(data_block.project_id)

    # Prepare doc_bin with specific records
    record_samples = data_block_util.prepare_records(
        data_block_id=data_block_id,
        attribute_id=attribute_id,
        record_indices=record_indices,
        limit=10,
    )

    # Run calculation with LLM playground config
    calculated_attributes = attribute_util.run_attribute_calculation_exec_env(
        attribute_id=None,
        project_id=project_id,
        doc_bin=record_samples,
        llm_playground_config=llm_playground_config,
        data_block_id=data_block_id,
        data_block_attribute_id=attribute_id,
    )

    return calculated_attributes
