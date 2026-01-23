import random
from typing import Dict, List, Optional, Any

import os
from sqlalchemy.orm.attributes import flag_modified

from controller.data_block.sql import execute_query
from controller.data_block import attribute as data_block_attribute_manager
from controller.task_master import manager as task_master_manager

from submodules.s3 import controller as s3
from submodules.model import DataBlock
from submodules.model.enums import (
    NotificationType,
    DataBlockType,
    AttributeState,
    TaskType,
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


def update_query_results(
    org_id: str,
    user_id: str,
    data_block_id: str,
    sql_config: Optional[Dict[str, Dict[str, Any]]] = None,
    include_schema: bool = True,
) -> List[Dict[str, Any]]:
    # TODO: don't update sql_data for LIVE queries
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
    )
    data_block = update(
        org_id,
        user_id,
        data_block_id=data_block_id,
        sql_data=results,
        overwrite_sql=True,
        with_commit=True,
    )

    if data_block.type == DataBlockType.STABLE.value:
        for attribute in data_block_attributes_db_bo.get_all(
            data_block_id=data_block_id,
            state_filter=[AttributeState.USABLE.value],
        ):
            # TODO: send as task list instead of individual tasks
            task_master_manager.queue_task(
                str(org_id),
                str(user_id),
                TaskType.ATTRIBUTE_CALCULATION,
                {
                    "project_id": str(data_block.project_id),
                    "attribute_id": str(attribute.id),
                    "data_block_id": data_block_id,
                },
                True,
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
) -> Optional[DataBlock]:
    data_block = data_block_db_bo.get(org_id, data_block_id)
    if not data_block:
        create_notification(
            NotificationType.DATA_BLOCK_NOT_FOUND,
            user_id,
            data_block.project_id,
            data_block.type.value,
        )
        return

    return data_block_db_bo.update(
        org_id,
        data_block_id,
        name,
        description,
        sql_config,
        sql_data,
        overwrite_sql,
        with_commit=with_commit,
    )


def delete_many(org_id: str, project_id: str, ids: Optional[List[str]] = None) -> None:
    for id in ids:
        data_block_attribute_manager.delete_many(id)
        s3.delete_object(
            org_id, str(project_id) + "/data-blocks/" + id + "/docbin_full"
        )

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


def get_record(data_block_id: str, record_id: Optional[str] = None):
    data_block = data_block_db_bo.get_by_id(data_block_id)
    if not data_block or not data_block.sql_data:
        raise EntityNotFoundException(f"Data block {data_block_id} not found")

    if not record_id:
        record = random.choice(data_block.sql_data)
    else:
        record = next(
            filter(
                lambda x: str(x["record_id"]) == str(record_id), data_block.sql_data
            ),
            None,
        )
    if not record:
        raise EntityNotFoundException(f"Record {record_id} not found in data block")
    return record
