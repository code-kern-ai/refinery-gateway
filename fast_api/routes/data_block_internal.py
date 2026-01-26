from fastapi import APIRouter

from fast_api.models import DataBlockExecuteQueryRequestInternal
from fast_api.routes.client_response import pack_json_result
from controller.data_block import manager as data_block_manager

router = APIRouter()


@router.post("/query/{data_block_id}")
def execute_query(data_block_id: str, data: DataBlockExecuteQueryRequestInternal):
    results = data_block_manager.update_query_results(
        org_id=data.org_id,
        user_id=data.user_id,
        data_block_id=data_block_id,
    )
    return pack_json_result(results, wrap_for_frontend=False)
