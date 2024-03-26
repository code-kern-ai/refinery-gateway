import json
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from controller.auth import manager as auth_manager
from controller.record import manager as manager
from controller.comment import manager as comment_manager
from fast_api.routes.client_response import pack_json_result

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
