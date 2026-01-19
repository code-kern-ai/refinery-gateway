from typing import Dict, List, Union, Optional, Any

import os

from submodules.model import DataBlock
from submodules.model.enums import (
    NotificationType,
    DataBlockType,
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
from submodules.model.util import sql_alchemy_to_dict
from submodules.model.sql_validator import validate_sql_clause
from util.notification import create_notification

COGNITION_GATEWAY = os.getenv("COGNITION_GATEWAY", "http://cognition-gateway:80")


def get(org_id: str, data_block_id: str) -> DataBlock:
    data_block: DataBlock = data_block_db_bo.get(org_id, data_block_id)
    if data_block_id and not data_block:
        raise EntityNotFoundException

    return data_block


def get_result(data_block_id: str) -> DataBlock:
    return data_block_db_bo.get_result_by_data_block_id(data_block_id)


def get_by_project_id(org_id: str, project_id: str) -> List[DataBlock]:
    data_blocks: List[DataBlock] = data_block_db_bo.get_by_project_id(
        org_id, project_id
    )
    return data_blocks


def infer_query_schema(query: str) -> List[Dict[str, Union[str, DataTypes]]]:
    schema = []
    result = sql_alchemy_to_dict(general.execute_first(query))

    # Extract column information from result metadata
    for column_name, value in result.items():
        schema.append(
            {
                "column_name": column_name,
                "column_data_type": _infer_type_from_value(value),
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


def execute_query(
    org_id: str, data_block_id: str, include_schema: bool = True
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    data_block = get(org_id, data_block_id)
    if not data_block:
        raise EntityNotFoundException

    data_block_query = construct_data_block_query(data_block)
    data_block_result = data_block_db_bo.get_result(
        data_block.project_id, data_block.id
    )

    if not data_block_result:
        data_block_result = data_block_db_bo.create_result(
            data_block.project_id,
            data_block.id,
            sql_used=data_block_query,
            data=list(
                map(lambda x: x._asdict(), general.execute_all(data_block_query))
            ),
            with_commit=True,
        )

    if DataBlockType.from_string(data_block.type) == DataBlockType.LIVE:
        data_block_result = data_block_db_bo.update_result(
            data_block.project_id,
            data_block.id,
            data=list(
                map(lambda x: x._asdict(), general.execute_all(data_block_query))
            ),
            with_commit=True,
        )
    elif (
        DataBlockType.from_string(data_block.type) == DataBlockType.STABLE
        and data_block_result.sql_used != data_block_query
    ):
        data_block_result = data_block_db_bo.update_result(
            data_block.project_id,
            data_block.id,
            sql_used=data_block_query,
            data=list(
                map(lambda x: x._asdict(), general.execute_all(data_block_query))
            ),
            with_commit=True,
        )

    if include_schema:
        schema = infer_query_schema(data_block_query)
        data_block_attributes_db_bo.sync_attributes_from_schema(
            data_block_id,
            schema,
            with_commit=True,
        )

    return data_block_result.data


def create(
    org_id: str,
    user_id: str,
    project_id: str,
    name: str,
    description: str,
    type: DataBlockType,
) -> None:
    data_block = data_block_db_bo.create(
        org_id, user_id, project_id, name, description, type, with_commit=True
    )
    return data_block


def update(
    org_id: str,
    user_id: str,
    data_block_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    sql_config: Optional[Dict[str, Dict[str, str]]] = None,
    overwrite_sql_config: bool = False,
) -> None:
    data_block = data_block_db_bo.get(org_id, data_block_id)
    if not data_block:
        create_notification(
            NotificationType.DATA_BLOCK_NOT_FOUND,
            user_id,
            data_block.project_id,
            data_block.type.value,
        )
        return

    data_block_db_bo.update(
        org_id,
        data_block_id,
        name,
        description,
        sql_config,
        overwrite_sql_config,
        with_commit=True,
    )


def delete_many(org_id: str, project_id: str, ids: List[str]) -> None:
    data_block_db_bo.delete_many(org_id, project_id, ids, with_commit=True)


def construct_data_block_query(data_block: DataBlock) -> str:
    extend_allowed_nodes = {"select", "where", "group", "order", "ordered"}
    select_clause = data_block.sql_config.get("config", {}).get("select_clause")
    if select_not_valid := validate_sql_clause(
        select=select_clause,
        include_db_check=False,
        extend_allowed_nodes=extend_allowed_nodes,
        extend_disallowed_column_prefix=set(["record_id"]),
    ):
        raise ValueError(
            f"Invalid SELECT clause in data block SQL config: {select_not_valid}"
        )

    where_clause = data_block.sql_config.get("config", {}).get("where_clause")
    if where_clause:
        if where_not_valid := validate_sql_clause(
            where=where_clause,
            extend_allowed_nodes=extend_allowed_nodes,
            include_db_check=False,
        ):
            raise ValueError(
                f"Invalid WHERE clause in data block SQL config: {where_not_valid}"
            )

    group_by_clause = data_block.sql_config.get("config", {}).get("group_by_clause")
    if group_by_clause:
        if group_by_not_valid := validate_sql_clause(
            group_by=group_by_clause,
            extend_allowed_nodes=extend_allowed_nodes,
            include_db_check=False,
        ):
            raise ValueError(
                f"Invalid GROUP BY clause in data block SQL config: {group_by_not_valid}"
            )

    order_by_clause = data_block.sql_config.get("config", {}).get("order_by_clause")
    if order_by_clause:
        if order_by_not_valid := validate_sql_clause(
            order_by=order_by_clause,
            extend_allowed_nodes=extend_allowed_nodes,
            include_db_check=False,
        ):
            raise ValueError(
                f"Invalid ORDER BY clause in data block SQL config: {order_by_not_valid}"
            )

    try:
        return record_db_bo.get_record_data_by_sanitized_params(
            str(data_block.project_id),
            sanitized_select=select_clause + ", r.id::varchar as record_id",
            sanitized_where=where_clause,
            order_by=order_by_clause,
            group_by=group_by_clause,
            limit=10,
            return_query=True,
        )
    except Exception as e:
        raise ValueError(f"Error fetching record data: {e}")
