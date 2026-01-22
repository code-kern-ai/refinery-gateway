from typing import Dict, List, Optional, Any

import os
from sqlalchemy.orm.attributes import flag_modified

from controller.data_block.sql import execute_query

from submodules.model import DataBlock
from submodules.model.enums import (
    NotificationType,
    DataBlockType,
)
from submodules.model.exceptions import EntityNotFoundException
from submodules.model.business_objects import (
    data_block as data_block_db_bo,
    data_block_attributes as data_block_attributes_db_bo,
    general,
)
from util.notification import create_notification

COGNITION_GATEWAY = os.getenv("COGNITION_GATEWAY", "http://cognition-gateway:80")


def get(org_id: str, data_block_id: str) -> DataBlock:
    data_block: DataBlock = data_block_db_bo.get(org_id, data_block_id)
    if data_block_id and not data_block:
        raise EntityNotFoundException

    return data_block


def get_by_project_id(org_id: str, project_id: str) -> List[DataBlock]:
    data_blocks: List[DataBlock] = data_block_db_bo.get_all_by_project_id(
        org_id, project_id
    )
    return data_blocks


def get_query_results(
    org_id: str,
    user_id: str,
    data_block_id: str,
    sql_config: Dict[str, Dict[str, Any]],
    include_schema: bool = True,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    update(
        org_id,
        user_id,
        data_block_id,
        sql_config=sql_config,
        sql_data=[],
        overwrite_sql=True,
        with_commit=True,
    )
    results = execute_query(
        org_id,
        data_block_id,
        include_schema=include_schema,
        limit=limit,
    )
    update(
        org_id,
        user_id,
        data_block_id=data_block_id,
        sql_data=results,
        overwrite_sql=True,
        with_commit=True,
    )
    return results


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
    sql_config: Optional[Dict[str, Dict[str, Any]]] = None,
    sql_data: Optional[Dict[str, Any]] = None,
    overwrite_sql: bool = False,
    with_commit=True,
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
        sql_data,
        overwrite_sql,
        with_commit=with_commit,
    )


def delete_many(org_id: str, project_id: str, ids: List[str]) -> None:
    data_block_db_bo.delete_many(org_id, project_id, ids, with_commit=True)


def update_add_user_created_attribute(
    data_block_id: str,
    attribute_id: str,
    calculated_attributes: Dict[str, str],
    with_commit: bool = False,
) -> None:
    data_block = data_block_db_bo.get_by_id(data_block_id)
    attribute_item = data_block_attributes_db_bo.get(data_block_id, attribute_id)
    changed = 0
    for record_id, attribute_value in calculated_attributes.items():
        record_item = next(
            filter(
                lambda x: str(x["record_id"]) == str(record_id), data_block.sql_data
            ),
            None,
        )
        if not record_item:
            # this can happen if an record was deleted or the tokenizer file isn't up to date
            continue
        record_item[attribute_item.name] = attribute_value
        flag_modified(data_block, "sql_data")
        if changed > 1000:
            changed = 0
            general.flush_or_commit(with_commit)
        changed += 1
    general.flush_or_commit(with_commit)


def delete_user_created_attribute(
    data_block_id: str, attribute_id: str, with_commit: bool = False
) -> None:
    data_block = data_block_db_bo.get_by_id(data_block_id)
    attribute_item = data_block_attributes_db_bo.get(data_block_id, attribute_id)

    if not attribute_item.user_created:
        return

    for i in range(len(data_block.sql_data)):
        del data_block.sql_data[i][attribute_item.name]
        flag_modified(data_block, "sql_data")
        if (i + 1) % 1000 == 0:
            general.flush_or_commit(with_commit)
    general.flush_or_commit(with_commit)
