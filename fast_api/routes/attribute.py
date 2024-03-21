from controller.attribute import manager
from typing import List, Union
from fast_api.routes.client_response import pack_json_result
from fastapi import APIRouter, Query
from submodules.model.util import sql_alchemy_to_dict

router = APIRouter()

ALL_ATTRIBUTES_WHITELIST = {
    "id",
    "name",
    "data_type",
    "is_primary_key",
    "relative_position",
    "user_created",
    "source_code",
    "state",
    "logs",
    "visibility",
}


@router.get("/{project_id}/all-attributes")
def get_attributes(
    project_id: str,
    state_filter: Union[List[str], None] = Query(default=None),
):

    data = manager.get_all_attributes(project_id, state_filter)
    data_dict = sql_alchemy_to_dict(data, column_whitelist=ALL_ATTRIBUTES_WHITELIST)
    return pack_json_result({"data": {"attributesByProjectId": data_dict}})
