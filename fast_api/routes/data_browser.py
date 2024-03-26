import json
from typing import Dict
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from controller.auth import manager as auth_manager
from controller.record import manager as manager
from controller.data_slice import manager as data_slice_manager
from controller.comment import manager as comment_manager
from fast_api.routes.client_response import pack_json_result
from util import notification
from submodules.model.enums import NotificationType

from submodules.model.util import (
    sql_alchemy_to_dict,
    to_frontend_obj_raw,
)


router = APIRouter()


@router.post("/{project_id}/record-comments")
async def get_record_comments(request: Request, project_id: str):
    body = await request.body()

    try:
        record_ids = json.loads(body)["recordIds"]
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"message": "Invalid JSON"},
        )

    user_id = auth_manager.get_user_id_by_info(request.state.info)
    data = comment_manager.get_record_comments(project_id, user_id, record_ids)
    return pack_json_result(
        {"data": {"getRecordComments": data}}, wrap_for_frontend=False
    )


@router.post("/{project_id}/search-records-extended")
async def search_records_extended(request: Request, project_id: str):
    body = await request.body()

    try:
        data = json.loads(body)
        filter_data = [json.loads(json_s) for json_s in data["filterData"]]
        offset = data["offset"]
        limit = data["limit"]
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"message": "Invalid JSON"},
        )

    user_id = auth_manager.get_user_id_by_info(request.state.info)

    results = manager.get_records_by_extended_search(
        project_id, user_id, filter_data, limit, offset
    )

    record_list = sql_alchemy_to_dict(results.record_list, for_frontend=False)
    record_list = to_frontend_obj_raw(record_list)
    record_list_pop = [
        {"recordData": json.dumps(item), "__typename": "ExtendedRecord"}
        for item in record_list
    ]

    data = {
        "recordList": record_list_pop,
        "queryLimit": results.query_limit,
        "queryOffset": results.query_offset,
        "fullCount": results.full_count,
        "sessionId": results.session_id,
    }

    return pack_json_result({"data": {"searchRecordsExtended": data}})


@router.post("/{project_id}/create-outlier-slice/{embedding_id}")
def create_outlier_slice(request: Request, project_id: str, embedding_id: str):
    user_id = auth_manager.get_user_id_by_info(request.state.info)

    data_slice_item = data_slice_manager.create_outlier_slice(
        project_id, user_id, embedding_id
    )
    if not data_slice_item:
        notification.create_notification(
            NotificationType.CUSTOM,
            user_id,
            project_id,
            "Not enough unlabeled records. No outliers detected.",
        )
    else:
        notification.send_organization_update(
            project_id, f"data_slice_created:{str(data_slice_item.id)}"
        )

    return JSONResponse(
        status_code=201,
        content={"message": "Outlier slice created"},
    )


@router.post("/{project_id}/records-by-static-slice/{slice_id}")
async def get_records_by_static_slice(request: Request, project_id: str, slice_id: str):
    body = await request.body()

    try:
        data = json.loads(body)
        order_by: Dict[str, str] = data.get("orderBy", {})
        offset = data.get("offset", 0)
        limit = data.get("limit", 0)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"message": "Invalid JSON"},
        )

    user_id = auth_manager.get_user_id_by_info(request.state.info)

    results = manager.get_records_by_static_slice(
        user_id, project_id, slice_id, order_by, limit, offset
    )

    record_list = sql_alchemy_to_dict(results.record_list, for_frontend=False)
    record_list = to_frontend_obj_raw(record_list)
    record_list_pop = [
        {"recordData": json.dumps(item), "__typename": "ExtendedRecord"}
        for item in record_list
    ]

    data = {
        "recordList": record_list_pop,
        "queryLimit": results.query_limit,
        "queryOffset": results.query_offset,
        "fullCount": results.full_count,
        "sessionId": results.session_id,
    }

    return pack_json_result({"data": {"recordsByStaticSlice": data}})
