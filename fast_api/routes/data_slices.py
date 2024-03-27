from typing import Optional

from fastapi import APIRouter, Request
from fast_api.routes.client_response import pack_json_result, wrap_content_for_frontend
from submodules.model.util import sql_alchemy_to_dict
from typing import List
from controller.data_slice import manager
from controller.record import manager as record_manager
import json


router = APIRouter()


@router.get("/{project_id}")
def data_slices(
    request: Request, project_id: str, slice_type: Optional[str] = None
) -> List:

    values = [
        sql_alchemy_to_dict(ds)
        for ds in manager.get_all_data_slices(project_id, slice_type)
    ]
    for v in values:
        v["filterData"] = json.dumps(v["filter_data"])
        v["filterRaw"] = json.dumps(v["filter_raw"])
        del v["filter_data"]
        del v["filter_raw"]
        del v["count_sql"]
    return pack_json_result(
        {"data": {"dataSlices": wrap_content_for_frontend(values)}},
    )


@router.get("/{project_id}/unique-values")
def get_unique_values_by_attributes(project_id: str):
    data = record_manager.get_unique_values_by_attributes(project_id)
    return pack_json_result({"data": {"uniqueValuesByAttributes": data}})


@router.get("/{project_id}/static-data-slices-current-count/{slice_id}")
def get_static_data_slices_current_count(
    request: Request, project_id: str, slice_id: str
):
    data = manager.count_items(project_id, slice_id)
    return pack_json_result({"data": {"staticDataSlicesCurrentCount": data}})
