import json
from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import JSONResponse
from controller.auth import manager as auth_manager
from controller.record import manager as manager
from controller.data_slice import manager as data_slice_manager
from controller.comment import manager as comment_manager
from exceptions.exceptions import TooManyRecordsForStaticSliceException
from fast_api.models import (
    CreateDataSliceBody,
    ListStringBody,
    RecordsByStaticSliceBody,
    SearchRecordsBySimilarityBody,
    SearchRecordsExtendedBody,
    UpdateDataSliceBody,
)
from fast_api.routes.client_response import pack_json_result
from service.search.search import resolve_extended_search
from submodules.model.business_objects import general
from util import notification
from submodules.model.enums import NotificationType

from submodules.model.util import (
    sql_alchemy_to_dict,
    to_frontend_obj_raw,
)


router = APIRouter()


@router.post(
    "/{project_id}/record-comments",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_record_comments(
    request: Request,
    project_id: str,
    body: ListStringBody = Body(...),
):
    record_ids = body.value

    user_id = auth_manager.get_user_id_by_info(request.state.info)
    data = comment_manager.get_record_comments(project_id, user_id, record_ids)
    return pack_json_result(
        {"data": {"getRecordComments": data}}, wrap_for_frontend=False
    )


@router.post(
    "/{project_id}/search-records-extended",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def search_records_extended(
    request: Request,
    project_id: str,
    body: SearchRecordsExtendedBody = Body(...),
):
    filter_data = [json.loads(item) for item in body.filterData]
    limit = body.limit
    offset = body.offset

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


@router.post(
    "/{project_id}/search-records-extended-cog",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def search_records_extended_cog(
    request: Request,
    project_id: str,
    body: SearchRecordsExtendedBody = Body(...),
):
    filter_data = [json.loads(item) for item in body.filterData]
    limit = body.limit
    offset = body.offset

    user_id = auth_manager.get_user_id_by_info(request.state.info)

    results = resolve_extended_search(project_id, user_id, filter_data, limit, offset)

    record_list = sql_alchemy_to_dict(results.record_list, for_frontend=False)
    record_list = to_frontend_obj_raw(record_list)
    record_list_pop = [{"recordData": json.dumps(item)} for item in record_list]

    data = {
        "queryLimit": results.query_limit,
        "queryOffset": results.query_offset,
        "fullCount": results.full_count,
        "sessionId": str(results.session_id),
        "recordList": record_list_pop,
    }

    return pack_json_result({"data": {"searchRecordsExtended": data}})


@router.post(
    "/{project_id}/create-outlier-slice/{embedding_id}",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def create_outlier_slice(
    request: Request,
    project_id: str,
    embedding_id: str,
):
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


@router.post(
    "/{project_id}/records-by-static-slice/{slice_id}",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_records_by_static_slice(
    request: Request,
    project_id: str,
    slice_id: str,
    body: RecordsByStaticSliceBody = Body(...),
):
    order_by = body.orderBy
    limit = body.limit
    offset = body.offset

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


@router.post(
    "/{project_id}/create-data-slice",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def create_data_slice(
    request: Request,
    project_id: str,
    body: CreateDataSliceBody = Body(...),
):
    name = body.name
    static = body.static
    filter_raw = json.loads(body.filterRaw)
    filter_data = [json.loads(item) for item in body.filterData]

    user = auth_manager.get_user_by_info(request.state.info)

    try:
        data_slice_item = data_slice_manager.create_data_slice(
            project_id, user.id, name, filter_raw, filter_data, static
        )
        notification.send_organization_update(
            project_id, f"data_slice_created:{str(data_slice_item.id)}"
        )
        data = {"id": str(data_slice_item.id), "__typename": "CreateDataSlice"}
        return pack_json_result(
            {"data": {"createDataSlice": data}}, wrap_for_frontend=False
        )
    except Exception as e:
        handle_error(e, user.id, project_id)
        return JSONResponse(
            status_code=400,
            content={"message": str(e)},
        )


@router.post(
    "/{project_id}/search-records-by-similarity",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_search_records_by_similarity(
    request: Request,
    project_id: str,
    body: SearchRecordsBySimilarityBody = Body(...),
):
    embedding_id = body.embeddingId
    record_id = body.recordId
    att_filter = body.attFilter
    record_sub_key = body.recordSubKey
    if att_filter:
        att_filter = json.loads(att_filter)

    user_id = auth_manager.get_user_by_info(request.state.info).id
    results = manager.get_records_by_similarity_search(
        project_id, user_id, embedding_id, record_id, att_filter, record_sub_key
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

    return pack_json_result({"data": {"searchRecordsBySimilarity": data}})


@router.post(
    "/{project_id}/update-data-slice",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def update_data_slice(
    request: Request,
    project_id: str,
    dataSliceBody: UpdateDataSliceBody = Body(...),
):

    user = auth_manager.get_user_by_info(request.state.info)
    ok = False

    try:
        raw = json.loads(dataSliceBody.filter_raw)
        if not isinstance(raw, dict):
            raise Exception("Invalid filter_raw")
        data = [json.loads(d) for d in dataSliceBody.filter_data]
        data_slice_manager.update_data_slice(
            project_id,
            dataSliceBody.data_slice_id,
            data,
            dataSliceBody.filter_raw,
            dataSliceBody.static,
        )
        notification.send_organization_update(
            project_id, f"data_slice_updated:{dataSliceBody.data_slice_id}"
        )
        ok = True
    except Exception as e:
        handle_error(e, user.id, project_id)

    return pack_json_result({"data": {"updateDataSlice": {"ok": ok}}})


def handle_error(exception: Exception, user_id: str, project_id: str):
    general.rollback()
    if isinstance(exception,TooManyRecordsForStaticSliceException):
        error = "Too many records for a static slice"
    else:
        error = str(exception.__class__.__name__)

    notification.create_notification(
        NotificationType.DATA_SLICE_UPDATE_FAILED,
        user_id,
        project_id,
        error,
    )
