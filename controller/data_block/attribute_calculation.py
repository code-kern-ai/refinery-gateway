"""Shared utilities for attribute calculation across different data sources."""

import json
from typing import Dict, List, Any, Tuple

from submodules.model.enums import DataTypes
from submodules.s3 import controller as s3
from submodules.model.util import sql_alchemy_to_dict


def prepare_samples_from_data(
    org_id: str,
    project_id: str,
    data_block_attribute_id: str,
    records: List[Dict[str, Any]],
) -> str:
    doc_json = json.dumps(
        sql_alchemy_to_dict(
            [
                {"bytes": "", "columns": list(record.keys()), **record}
                for record in records
            ]
        )
    )
    prefixed_samples = f"{data_block_attribute_id}_doc_bin.json"

    s3.put_object(org_id, f"{project_id}/data-blocks/{prefixed_samples}", doc_json)

    return prefixed_samples


def format_calculation_results(
    calculated_attributes: Dict[str, Any],
    attribute_data_type: str,
) -> Tuple[List[str], List[Any]]:
    """
    Format calculated attributes for API response.

    Args:
        calculated_attributes: Dict mapping record_id to calculated value
        attribute_data_type: The data type of the attribute

    Returns:
        Tuple of (record_ids, values)
    """
    if attribute_data_type in (
        DataTypes.EMBEDDING_LIST.value,
        DataTypes.TEXT_LIST.value,
    ):
        # JSON serialize list values for frontend transfer
        values = [json.dumps(v) for v in calculated_attributes.values()]
    else:
        values = list(calculated_attributes.values())

    return list(calculated_attributes.keys()), values
