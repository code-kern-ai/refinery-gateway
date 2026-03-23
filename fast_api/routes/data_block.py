from fastapi import APIRouter, Request, Body, Depends, Query

from fast_api.models import (
    DataBlockCreateRequest,
    DataBlockUpdateRequest,
    DataBlockDeleteRequest,
    DataBlockExecuteQueryRequest,
    DataBlockAttributeCreateRequest,
    DataBlockAttributeUpdateRequest,
    DataBlockAttributeDeleteRequest,
    RunLlmPlaygroundBody,
)
from fast_api.routes.client_response import get_silent_success, pack_json_result
from controller.data_block import manager as data_block_manager
from controller.data_block import attribute as data_block_attribute_manager
from controller.auth import manager as auth_manager

from submodules.model.util import sql_alchemy_to_dict
import json

router = APIRouter()


@router.get(
    "/single/{project_id}/{data_block_id}",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get(request: Request, project_id: str, data_block_id: str):
    user = auth_manager.get_user_by_info(request.state.info)
    data_block = data_block_manager.get(user.organization_id, project_id, data_block_id)
    data = data_block.sql_data.copy() if data_block.sql_data else None
    data_block = sql_alchemy_to_dict(
        data_block,
        for_frontend=True,
        dont_wrap_uuids=False,
        column_blacklist=["sql_data"],
    )
    data_block["sqlData"] = data
    data_block["sqlSchema"] = sql_alchemy_to_dict(
        data_block_attribute_manager.get_schema(data_block_id),
        for_frontend=True,
        dont_wrap_uuids=False,
    )

    return pack_json_result(
        data_block,
        wrap_for_frontend=False,
    )


@router.get(
    "/project/{project_id}",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_by_project_id(request: Request, project_id: str):
    user = auth_manager.get_user_by_info(request.state.info)
    return pack_json_result(
        data_block_manager.get_by_project_id(user.organization_id, project_id)
    )


@router.get(
    "/project/{project_id}/mini",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_project_data_blocks_mini(
    request: Request, project_id: str, only_executed: bool
):
    user = auth_manager.get_user_by_info(request.state.info)

    data_blocks = data_block_manager.get_by_project_id(
        user.organization_id, project_id, only_executed=only_executed
    )
    data_blocks_extended = [
        {"id": str(data_block.get("id")), "name": str(data_block.get("name"))}
        for data_block in sql_alchemy_to_dict(data_blocks)
    ]
    return pack_json_result(data_blocks_extended)


@router.post(
    "/query/{project_id}/{data_block_id}",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def execute_query(
    request: Request,
    project_id: str,
    data_block_id: str,
    data: DataBlockExecuteQueryRequest,
):
    user = auth_manager.get_user_by_info(request.state.info)
    results = data_block_manager.update_query_results(
        org_id=user.organization_id,
        user_id=user.id,
        project_id=project_id,
        data_block_id=data_block_id,
        sql_config=data.sql_config,
        sync_schema=True,
    )
    return pack_json_result(results)


@router.post(
    "/{project_id}",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def create(request: Request, project_id: str, data: DataBlockCreateRequest):
    user = auth_manager.get_user_by_info(request.state.info)
    data_block = data_block_manager.create(
        user.organization_id,
        user.id,
        project_id,
        data.name,
        data.description,
        data.type,
    )
    return pack_json_result({"id": str(data_block.id)}, wrap_for_frontend=False)


@router.put(
    "/project/{project_id}/{data_block_id}",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def update(
    request: Request, project_id: str, data_block_id: str, data: DataBlockUpdateRequest
):
    user = auth_manager.get_user_by_info(request.state.info)
    data_block_manager.update(
        user.organization_id,
        project_id,
        data_block_id,
        data.name,
        data.description,
        data.sql_config,
        # overwrite_sql=True,
    )
    return get_silent_success()


@router.delete(
    "/{project_id}",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def delete_many(request: Request, project_id: str, data: DataBlockDeleteRequest):
    user = auth_manager.get_user_by_info(request.state.info)
    data_block_manager.delete_many(user.organization_id, project_id, data.ids)
    return get_silent_success()


# --- DataBlockAttributes Routes ---


@router.get(
    "/project/{project_id}/{data_block_id}/attributes/schema",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_attributes_schema(request: Request, data_block_id: str):
    auth_manager.get_user_by_info(request.state.info)
    schema = data_block_attribute_manager.get_schema(data_block_id)
    return pack_json_result(schema)


@router.get(
    "/{project_id}/{data_block_id}/attributes/{attribute_id}",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_attribute(request: Request, data_block_id: str, attribute_id: str):
    auth_manager.get_user_by_info(request.state.info)
    attribute = data_block_attribute_manager.get(data_block_id, attribute_id)
    return pack_json_result(attribute)


@router.post(
    "/{project_id}/{data_block_id}/attributes",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def create_attribute(
    request: Request, data_block_id: str, data: DataBlockAttributeCreateRequest
):
    auth_manager.get_user_by_info(request.state.info)
    attribute = data_block_attribute_manager.create(
        data_block_id=data_block_id,
        name=data.name,
        data_type=data.data_type,
        user_created=data.user_created,
        source_code=data.source_code,
        state=data.state,
        additional_config=data.additional_config,
    )
    return pack_json_result({"id": str(attribute.id)}, wrap_for_frontend=False)


@router.put(
    "/{project_id}/{data_block_id}/attributes/{attribute_id}",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def update_attribute(
    request: Request,
    data_block_id: str,
    attribute_id: str,
    data: DataBlockAttributeUpdateRequest,
):
    auth_manager.get_user_by_info(request.state.info)
    attribute = data_block_attribute_manager.update(
        data_block_id=data_block_id,
        attribute_id=attribute_id,
        name=data.name,
        data_type=data.data_type,
        relative_position=data.relative_position,
        source_code=data.source_code,
        state=data.state,
        logs=data.logs,
        progress=data.progress,
        additional_config=data.additional_config,
    )
    return pack_json_result(sql_alchemy_to_dict(attribute))


@router.delete(
    "/{project_id}/{data_block_id}/attributes/{attribute_id}",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def delete_attribute(request: Request, data_block_id: str, attribute_id: str):
    auth_manager.get_user_by_info(request.state.info)
    data_block_attribute_manager.delete_attributes(data_block_id, [attribute_id])
    return get_silent_success()


@router.get(
    "/{project_id}/{data_block_id}/attributes/{data_block_attribute_id}/sample-records",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_sample_records(
    request: Request,
    project_id: str,
    data_block_id: str,
    data_block_attribute_id: str,
):
    user = auth_manager.get_user_by_info(request.state.info)
    record_ids, calculated_attributes = (
        data_block_attribute_manager.calculate_sample_records(
            user.organization_id,
            project_id,
            data_block_id,
            attribute_id=data_block_attribute_id,
            limit=10,
        )
    )
    return pack_json_result(
        {
            "record_ids": record_ids,
            "calculated_attributes": calculated_attributes,
        }
    )


@router.post(
    "/{project_id}/{data_block_id}/attributes/{attribute_id}/run-llm-playground",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def run_llm_playground(
    request: Request,
    data_block_id: str,
    attribute_id: str,
    body: RunLlmPlaygroundBody = Body(...),
):
    auth_manager.get_user_by_info(request.state.info)
    return pack_json_result(
        data_block_attribute_manager.run_llm_playground(
            data_block_id=data_block_id,
            attribute_id=attribute_id,
            llm_playground_config=body.llm_config,
            record_ids=body.record_ids,
        ),
        wrap_for_frontend=False,
    )


@router.get(
    "/{project_id}/{data_block_id}/record-by-record-id",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_record_by_record_id(
    data_block_id: str,
    record_id: str = None,
):
    record = data_block_manager.get_record(data_block_id, record_id)

    data = {
        "id": str(record["record_id"]),
        "data": json.dumps(record),
        "data_block_id": data_block_id,
    }

    return pack_json_result(data)
