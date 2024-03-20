from controller.attribute import manager
from typing import List, Union
from fast_api.routes.client_response import pack_json_result
from fastapi import APIRouter, Query
from submodules.model.util import sql_alchemy_to_dict

router = APIRouter()


@router.get("/all-attributes/{project_id}")
def get_attributes(
    project_id: str,
    state_filter: Union[List[str], None] = Query(default=None),
):

    data = manager.get_all_attributes(project_id, state_filter)
    data_dict = sql_alchemy_to_dict(data)
    return pack_json_result({"data": {"attributesByProjectId": data_dict}})
