import json


from controller.auth import manager as auth_manager
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from submodules.model import enums
from fast_api.routes.client_response import pack_json_result
from controller.labeling_access_link import manager
from controller.project import manager as project_manager

from submodules.model.business_objects import (
    information_source as information_source,
    user as user_manager,
    data_slice,
)
from submodules.model.util import sql_alchemy_to_dict, to_frontend_obj_raw


router = APIRouter()

AVAILABLE_LINKS_WHITELIST = ["id", "link", "link_type", "name", "is_locked"]


@router.post("/{project_id}/available-links")
async def get_available_links(request: Request, project_id: str):
    body = await request.json()

    try:
        assumed_role = body.get("assumedRole", "")
        assumed_heuristic_id = body.get("assumedHeuristicId", "")
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"message": "Invalid JSON"},
        )

    if assumed_heuristic_id == manager.DUMMY_LINK_ID:
        return pack_json_result({"data": {"availableLinks": []}})
    if assumed_heuristic_id:
        is_item = information_source.get(project_id, assumed_heuristic_id)
        if (
            not is_item
            or is_item.type != enums.InformationSourceType.CROWD_LABELER.value
        ):
            raise ValueError("Unknown heuristic id")
        settings = json.loads(is_item.source_code)
        user = user_manager.get(settings["annotator_id"])
    else:
        user = auth_manager.get_user_by_info(request.state.info)

    user_role = assumed_role if assumed_role else user.role

    available_links = manager.get_by_all_by_user_id(project_id, str(user.id), user_role)

    available_links = sql_alchemy_to_dict(
        available_links,
        for_frontend=False,
    )
    available_links = to_frontend_obj_raw(available_links)

    def get_name(link_type, data_slice_id, heuristic_id):
        if link_type == enums.LinkTypes.HEURISTIC.value:
            return information_source.get(project_id, heuristic_id).name
        elif link_type == enums.LinkTypes.DATA_SLICE.value:
            return data_slice.get(project_id, data_slice_id).name
        return "Unknown type"

    for obj in available_links:
        obj["name"] = get_name(
            obj.get("link_type"), obj.get("data_slice_id"), obj.get("heuristic_id")
        )

        iter_keys = list(obj.keys())
        for key in iter_keys:
            if key not in AVAILABLE_LINKS_WHITELIST:
                obj.pop(key, None)

    return pack_json_result({"data": {"availableLinks": available_links}})


@router.post("/{project_id}/huddle-data")
async def get_huddle_data(request: Request, project_id: str):
    body = await request.json()

    try:
        huddle_id = body.get("huddleId", "")
        huddle_type = body.get("huddleType", "")
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"message": "Invalid JSON"},
        )

    user_id = str(auth_manager.get_user_by_info(request.state.info).id)
    huddle_data = project_manager.resolve_request_huddle_data(
        project_id, user_id, huddle_id, huddle_type
    )

    data = {
        "huddleId": huddle_id,
        "huddleType": huddle_type,
        "recordIds": huddle_data.record_ids,
        "startPos": huddle_data.start_pos,
        "allowedTask": huddle_data.allowed_task,
        "canEdit": huddle_data.can_edit,
        "checkedAt": huddle_data.checked_at,
    }

    return pack_json_result({"data": {"requestHuddleData": data}})
