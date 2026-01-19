from typing import Dict, List, Any, Optional, Tuple

from submodules.model import DataBlockAttribute
from submodules.model.enums import AttributeState, DataTypes
from submodules.model.exceptions import EntityNotFoundException
from submodules.model.business_objects import (
    data_block as data_block_db_bo,
    data_block_attributes as data_block_attributes_db_bo,
)
from controller.data_block import (
    util as data_block_util,
    attribute_calculation as data_block_attribute_calc,
)
from controller.attribute import util as attribute_util

# from controller.shared import attribute_calculation as shared_calc


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
    """
    Get attributes as a schema list (backward compatible format).
    """
    return data_block_attributes_db_bo.get_schema_as_list(data_block_id)


def create(
    data_block_id: str,
    name: str,
    data_type: str = DataTypes.TEXT.value,
    user_created: bool = False,
    source_code: Optional[str] = "",
    state: Optional[str] = None,
    additional_config: Optional[Dict[str, Any]] = None,
) -> DataBlockAttribute:
    # Get next relative position
    relative_position = (
        data_block_attributes_db_bo.get_relative_position(data_block_id) + 1
    )

    # Check if attribute with same name already exists
    existing = data_block_attributes_db_bo.get_by_name(data_block_id, name)
    if existing:
        raise ValueError(
            f"Attribute with name '{name}' already exists for this data block"
        )

    return data_block_attributes_db_bo.create(
        data_block_id=data_block_id,
        name=name,
        data_type=data_type,
        relative_position=relative_position,
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


def delete(data_block_id: str, attribute_id: str) -> None:
    attribute = data_block_attributes_db_bo.get(data_block_id, attribute_id)
    if not attribute:
        raise EntityNotFoundException

    data_block_attributes_db_bo.delete(data_block_id, attribute_id, with_commit=True)


def delete_many(data_block_id: str, attribute_ids: List[str]) -> None:
    data_block_attributes_db_bo.delete_many(
        data_block_id, attribute_ids, with_commit=True
    )


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


def calculate_sample_records(
    data_block_id: str,
    data_block_attribute_id: str,
) -> Tuple[List[str], List[Any]]:
    """
    Calculate attribute values for sample records from a data block.

    Args:
        data_block_id: The data block ID
        attribute_id: The attribute ID

    Returns:
        Tuple of (record_ids, calculated_values)
    """
    # Get data block for project_id
    data_block = data_block_db_bo.get_by_id(data_block_id)
    if not data_block:
        raise EntityNotFoundException(f"Data block {data_block_id} not found")

    project_id = str(data_block.project_id)

    # Prepare doc_bin from DataBlockResults
    doc_samples = data_block_util.prepare_sample_records(
        data_block_attribute_id=data_block_attribute_id,
        data_block_id=data_block_id,
    )

    # Run calculation using shared execution environment
    calculated_attributes = attribute_util.run_attribute_calculation_exec_env(
        attribute_id=None,
        data_block_attribute_id=data_block_attribute_id,
        data_block_id=data_block_id,
        project_id=project_id,
        doc_bin=doc_samples,
    )

    # Get attribute for data type
    attribute = data_block_attributes_db_bo.get(data_block_id, data_block_attribute_id)

    return data_block_attribute_calc.format_calculation_results(
        calculated_attributes,
        attribute.data_type,
    )


def run_llm_playground(
    data_block_id: str,
    data_block_attribute_id: str,
    llm_playground_config: Dict[str, Any],
    record_indices: List[int],
) -> Dict[str, Any]:
    data_block = data_block_db_bo.get_by_id(data_block_id)
    if not data_block:
        raise EntityNotFoundException(f"Data block {data_block_id} not found")

    project_id = str(data_block.project_id)

    # Prepare doc_bin with specific records
    record_samples = data_block_util.prepare_sample_records(
        data_block_attribute_id=data_block_attribute_id,
        data_block_id=data_block_id,
        record_indices=record_indices,
    )

    # Run calculation with LLM playground config
    calculated_attributes = attribute_util.run_attribute_calculation_exec_env(
        data_block_attribute_id=data_block_attribute_id,
        project_id=project_id,
        doc_bin=record_samples,
        llm_playground_config=llm_playground_config,
    )

    return calculated_attributes
