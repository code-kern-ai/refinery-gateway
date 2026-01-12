from typing import Dict, List, Union
from sqlalchemy import text

import os

from submodules.model import DataBlock
from submodules.model.enums import NotificationType, DataBlockType
from submodules.model.exceptions import EntityNotFoundException
from submodules.model.business_objects import (
    data_block as data_block_db_bo,
    project as project_db_bo,
    record as record_db_bo,
    general,
)
from util.sql_helper.sql_helper_none_submodule import validate_sql_clause
from util.notification import create_notification
from util.service_requests import post_call_or_raise

COGNITION_GATEWAY = os.getenv("COGNITION_GATEWAY", "http://cognition-gateway:80")


def get(org_id: str, data_block_id: str) -> DataBlock:
    data_block: DataBlock = data_block_db_bo.get(org_id, data_block_id)
    if data_block_id and not data_block:
        raise EntityNotFoundException

    return data_block


def get_by_project_id(org_id: str, project_id: str) -> List[DataBlock]:
    data_blocks: List[DataBlock] = data_block_db_bo.get_by_project_id(
        org_id, project_id
    )
    return data_blocks


def get_data(org_id: str, data_block_id: str) -> Dict[str, List[Union[str, DataBlock]]]:
    data_block = get(org_id, data_block_id)
    if not data_block:
        raise EntityNotFoundException

    if DataBlockType.from_string(data_block.type) == DataBlockType.LIVE:
        data_block_query = construct_data_block_query(data_block)
        data_block_result = data_block_db_bo.update_result(
            data_block.project_id,
            data_block.id,
            data=list(
                map(lambda x: x._asdict(), general.execute_all(data_block_query))
            ),
            with_commit=True,
        )
    else:
        data_block_result = data_block_db_bo.get_result(
            data_block.project_id, data_block.id
        )
    return data_block_result.data if data_block_result else {}


def create(
    org_id: str,
    user_id: str,
    project_id: str,
    name: str,
    description: str,
    type: DataBlockType,
) -> None:
    if data_block_db_bo.get_by_project_id_and_type(org_id, project_id, type):
        create_notification(
            NotificationType.data_block_EXISTS,
            user_id,
            project_id,
            type.value,
        )
        return
    if not project_db_bo.is_integration_project(org_id, project_id):
        create_notification(
            NotificationType.data_block_NOT_SUPPORTED,
            user_id,
            project_id,
        )
        return

    data_block = data_block_db_bo.create(
        org_id, user_id, project_id, name, description, type, with_commit=True
    )
    return data_block


def update(
    org_id: str,
    user_id: str,
    data_block_id: str,
    name: str,
    description: str,
) -> None:
    data_block = data_block_db_bo.get(org_id, data_block_id)
    if not data_block:
        create_notification(
            NotificationType.data_block_NOT_FOUND,
            user_id,
            data_block.project_id,
            data_block.type.value,
        )
        return
    if not project_db_bo.is_integration_project(org_id, str(data_block.project_id)):
        create_notification(
            NotificationType.data_block_NOT_SUPPORTED,
            user_id,
            data_block.project_id,
        )
        return

    data_block_db_bo.update(org_id, data_block_id, name, description, with_commit=True)


def delete_many(org_id: str, project_id: str, ids: List[str]) -> None:
    data_block_db_bo.delete_many(org_id, project_id, ids, with_commit=True)


def construct_data_block_query(data_block: DataBlock) -> str:
    select_clause = data_block.sql_config.get("select", "r.data")
    if select_not_valid := validate_sql_clause(
        select=select_clause,
        include_db_check=False,
    ):
        raise ValueError(
            f"Invalid SELECT clause in data block SQL config: {select_not_valid}"
        )

    where_clause = data_block.sql_config.get("where")
    if where_clause:
        if where_not_valid := validate_sql_clause(
            where=where_clause,
            include_db_check=False,
        ):
            raise ValueError(
                f"Invalid WHERE clause in data block SQL config: {where_not_valid}"
            )

    order_by_clause = data_block.sql_config.get("order_by")
    if order_by_clause:
        if order_by_not_valid := validate_sql_clause(
            order_by=order_by_clause,
            include_db_check=False,
        ):
            raise ValueError(
                f"Invalid ORDER BY clause in data block SQL config: {order_by_not_valid}"
            )

    try:
        return record_db_bo.get_record_data_by_sanitized_params(
            str(data_block.project_id),
            where_clause,
            limit=10,
            sanitized_select=select_clause,
            order_by=order_by_clause,
            return_query=True,
        )
    except Exception as e:
        raise ValueError(f"Error fetching record data: {e}")
