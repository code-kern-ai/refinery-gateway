"""Utilities for data block attribute calculations."""

import random
from typing import Dict, List, Any, Optional

from submodules.model.business_objects import (
    data_block as data_block_db_bo,
)
from controller.data_block import attribute_calculation as data_block_attribute_calc


def get_sample_records(
    data_block_id: str,
    n: int = 10,
    record_indices: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    """
    Get sample records from DataBlockResults.

    Args:
        data_block_id: The data block ID
        n: Number of samples to retrieve (default 10)
        record_indices: Specific indices to retrieve (overrides n)

    Returns:
        List of sample record dictionaries
    """
    result = data_block_db_bo.get_result_by_data_block_id(data_block_id)
    if not result or not result.data:
        return []

    data = result.data

    if record_indices is not None:
        # Use specific indices
        return [data[i] for i in record_indices if i < len(data)]

    # Random sample
    sample_size = min(n, len(data))
    indices = random.sample(range(len(data)), sample_size)
    return [data[i] for i in indices]


def prepare_sample_records(
    data_block_attribute_id: str,
    data_block_id: str,
    record_indices: Optional[List[int]] = None,
    n: int = 10,
) -> str:
    data_block = data_block_db_bo.get_by_id(data_block_id)
    if not data_block:
        raise ValueError(f"Data block {data_block_id} not found")

    org_id = str(data_block.organization_id)
    project_id = str(data_block.project_id)

    sample_records = get_sample_records(data_block_id, n, record_indices)

    return data_block_attribute_calc.prepare_samples_from_data(
        org_id=org_id,
        project_id=project_id,
        data_block_attribute_id=data_block_attribute_id,
        records=sample_records,
    )
