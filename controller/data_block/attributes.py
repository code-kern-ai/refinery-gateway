from typing import Dict, List, Any, Optional

from submodules.model import DataBlockAttributes
from submodules.model.enums import AttributeState, DataTypes
from submodules.model.exceptions import EntityNotFoundException
from submodules.model.business_objects import (
    data_block_attributes as data_block_attributes_db_bo,
)


def get(data_block_id: str, attribute_id: str) -> DataBlockAttributes:
    attribute = data_block_attributes_db_bo.get(data_block_id, attribute_id)
    if attribute_id and not attribute:
        raise EntityNotFoundException
    return attribute


def get_all(
    data_block_id: str,
    state_filter: Optional[List[str]] = None,
) -> List[DataBlockAttributes]:
    return data_block_attributes_db_bo.get_all(data_block_id, state_filter)


def get_by_name(data_block_id: str, name: str) -> DataBlockAttributes:
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
) -> DataBlockAttributes:
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
        state=state or AttributeState.AUTOMATICALLY_CREATED.value,
        additional_config=additional_config,
        with_commit=True,
    )


def create_many(
    data_block_id: str,
    attributes: List[Dict[str, Any]],
) -> List[DataBlockAttributes]:
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
) -> DataBlockAttributes:
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
) -> List[DataBlockAttributes]:
    """
    Synchronize attributes from a schema definition.
    This replaces the old sql_schema column functionality.

    Args:
        data_block_id: The ID of the data block
        schema: List of dicts with column_name, column_data_type, and optionally state

    Returns:
        List of created/updated DataBlockAttributes
    """
    return data_block_attributes_db_bo.sync_attributes_from_schema(
        data_block_id=data_block_id,
        schema=schema,
        with_commit=True,
    )
