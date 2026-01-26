from typing import Dict, List, Optional, Any

import random
import json

from submodules.model.business_objects import data_block as data_block_db_bo
from submodules.model.util import sql_alchemy_to_dict
from submodules.s3 import controller as s3

from controller.data_block.sql import execute_query


def get_records(
    org_id: str,
    data_block_id: str,
    limit: int = 10,
    record_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    data = execute_query(org_id, data_block_id, limit=limit)
    if not data:
        return []

    if record_ids is not None:
        # Use specific indices
        return [record for record in data if record["id"] in map(int, record_ids)]

    # Random sample
    if limit:
        sample_size = min(limit, len(data))
        indices = random.sample(range(len(data)), sample_size)
        return [data[i] for i in indices]
    else:
        return data


def prepare_records(
    data_block_id: str,
    attribute_id: str,
    record_ids: Optional[List[int]] = None,
    limit: Optional[int] = None,
    prefix: Optional[str] = None,
) -> str:
    data_block = data_block_db_bo.get_by_id(data_block_id)
    if not data_block:
        raise ValueError(f"Data block {data_block_id} not found")

    org_id = str(data_block.organization_id)
    project_id = str(data_block.project_id)

    sample_records = get_records(org_id, data_block_id, limit, record_ids)

    return __prepare_records(
        org_id=org_id,
        project_id=project_id,
        attribute_id=attribute_id,
        records=sample_records,
        prefix=prefix,
    )


def __prepare_records(
    org_id: str,
    project_id: str,
    attribute_id: str,
    records: List[Dict[str, Any]],
    prefix: Optional[str] = None,
) -> str:
    doc_json = json.dumps(
        sql_alchemy_to_dict(
            [
                {"bytes": "", "columns": list(record.keys()), **record}
                for record in records
            ]
        )
    )
    minio_prefix = prefix or f"{attribute_id}_doc_bin.json"

    s3.put_object(org_id, f"{project_id}/data-blocks/{minio_prefix}", doc_json)

    return minio_prefix
