from controller.attribute import manager
from controller.auth import manager as auth_manager
from typing import List, Union
from fast_api.routes.client_response import pack_json_result
from fastapi import APIRouter, Query, Request
from submodules.model.enums import NotificationType
from submodules.model.util import sql_alchemy_to_dict
from util.notification import create_notification

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


@router.get("/{project_id}/check-composite-key")
def get_check_composite_key(request: Request, project_id: str):
    user = auth_manager.get_user_by_info(request.state.info)
    is_valid = manager.check_composite_key(project_id)
    if not is_valid:
        create_notification(
            NotificationType.INVALID_PRIMARY_KEY,
            user.id,
            project_id,
        )

    return pack_json_result({"data": {"checkCompositeKey": is_valid}})
