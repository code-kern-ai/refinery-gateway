from typing import Dict, List, Optional, Union, Any

from submodules.model import DataBlock
from submodules.model.util import sql_alchemy_to_dict
from submodules.model.enums import (
    DataTypes,
    AttributeState,
)
from submodules.model.exceptions import EntityNotFoundException
from submodules.model.business_objects import (
    data_block as data_block_db_bo,
    data_block_attributes as data_block_attributes_db_bo,
    record as record_db_bo,
    general,
)
from util import notification


def execute_query(
    org_id: str,
    data_block_id: str,
    sync_schema: bool = True,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    data_block = data_block_db_bo.get(org_id, data_block_id)
    if not data_block:
        raise EntityNotFoundException

    sql = construct_data_block_query(data_block, limit=limit)

    if sync_schema:
        schema = infer_query_schema(sql)
        sync_attributes_from_schema(
            data_block_id=data_block_id,
            schema=schema,
        )
    return sql_alchemy_to_dict(general.execute_all(sql), for_frontend=False)


def construct_data_block_query(
    data_block: DataBlock, limit: Optional[int] = None
) -> str:
    select_clause = data_block.sql_config.get("config", {}).get("select_clause")
    where_clause = data_block.sql_config.get("config", {}).get("where_clause")
    group_by_clause = data_block.sql_config.get("config", {}).get("group_by_clause")
    order_by_clause = data_block.sql_config.get("config", {}).get("order_by_clause")
    limit_clause = data_block.sql_config.get("config", {}).get("limit")

    try:
        sql_query = record_db_bo.get_record_data_by_sanitized_params(
            str(data_block.project_id),
            sanitized_select=select_clause,
            sanitized_where=where_clause,
            order_by=order_by_clause,
            sanitized_group_by=group_by_clause,
            limit=limit or limit_clause,
            return_query=True,
        )
        return (
            "SELECT ROW_NUMBER() OVER() AS record_id, * FROM ("
            + sql_query
            + ") AS sql_query_results"
        )
    except Exception as e:
        raise ValueError(f"Error fetching record data: {e}")


def infer_query_schema(query: str) -> List[Dict[str, Union[str, DataTypes]]]:
    schema = []
    result = sql_alchemy_to_dict(general.execute_first(query), for_frontend=False)

    # Extract column information from result metadata
    for column_name, value in result.items():
        schema.append(
            {
                "column_name": column_name,
                "column_data_type": _infer_type_from_value(value),
                "is_primary_key": (
                    column_name == "record_id"
                ),  # no logic performed on this key, here for potential future use
                "state": AttributeState.AUTOMATICALLY_CREATED.value,
            }
        )
    return schema


def _infer_type_from_value(value: Any) -> str:
    """Infer JSON Schema type from Python value."""
    if value is None:
        return DataTypes.UNKNOWN.value
    elif isinstance(value, bool):
        return DataTypes.BOOLEAN.value
    elif isinstance(value, int):
        return DataTypes.INTEGER.value
    elif isinstance(value, float):
        return DataTypes.NUMBER.value
    # elif isinstance(value, (dict, list)):
    #     return DataTypes.TEXT.value
    else:
        return DataTypes.TEXT.value


def sync_attributes_from_schema(
    data_block_id: str, schema: List[Dict[str, str]]
) -> None:
    """
    Synchronize attributes from a schema definition.
    This replaces the old sql_schema column functionality.

    Args:
        data_block_id: The ID of the data block
        schema: List of dicts with column_name, column_data_type, and optionally state

    Returns:
        List of created/updated DataBlockAttribute
    """
    data_block = data_block_db_bo.get_by_id(data_block_id)
    attrs = data_block_attributes_db_bo.sync_attributes_from_schema(
        data_block_id=data_block_id,
        schema=schema,
        with_commit=True,
    )
    # for attr in attrs:
    #     notification.send_organization_update(
    #         project_id=data_block.project_id,
    #         message=f"calculate_attribute:updated:{str(attr.id)}",
    #     )
    # notification.send_organization_update(
    #     project_id=data_block.project_id,
    #     message=f"calculate_attribute:finished:{str(attr.id)}",
    # )
