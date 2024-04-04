import json


from controller.auth import manager as auth_manager
from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse
from fast_api.models import GenerateAccessLinkBody, LinkRouteBody
from submodules.model import enums
from fast_api.routes.client_response import pack_json_result
from controller.labeling_access_link import manager
from controller.project import manager as project_manager
from submodules.model.business_objects import record
from controller.tokenization import manager as tokenization_manager

from controller.record_label_association import manager as rla_manager
from controller.record import manager as record_manager
from submodules.model.business_objects import (
    information_source as information_source,
    user as user_manager,
    data_slice,
)
from submodules.model.util import sql_alchemy_to_dict, to_frontend_obj_raw
from util import notification


router = APIRouter()

AVAILABLE_LINKS_WHITELIST = ["id", "link", "link_type", "name", "is_locked"]


@router.post("/{project_id}/available-links")
async def get_available_links(request: Request, project_id: str):
    try:
        body = await request.json()
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
    try:
        body = await request.json()
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
        "huddleId": huddle_data.huddle_id,
        "recordIds": huddle_data.record_ids,
        "huddleType": huddle_type,
        "startPos": huddle_data.start_pos,
        "allowedTask": huddle_data.allowed_task,
        "canEdit": huddle_data.can_edit,
        "checkedAt": huddle_data.checked_at.isoformat(),
    }

    return pack_json_result({"data": {"requestHuddleData": data}})


@router.post("/tokenized-record")
async def get_tokenized_record(request: Request):
    try:
        body = await request.json()
        record_id = body.get("recordId", "")
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"message": "Invalid JSON"},
        )

    record_item = record.get_without_project_id(record_id)
    if not record_item:
        return pack_json_result({"data": {"tokenizeRecord": None}})

    # specific scenario where we should not delegate this call up to middleware
    auth_manager.check_project_access(request.state.info, record_item.project_id)

    tokenize_data = tokenization_manager.get_tokenized_record(
        record_item.project_id, record_id
    )

    attributes = []

    for attr in tokenize_data.attributes:
        tokens = [
            {
                "value": token.value,
                "idx": token.idx,
                "posStart": token.pos_start,
                "posEnd": token.pos_end,
                "type": token.type,
            }
            for token in attr.tokens
        ]
        attributes.append(
            {
                "raw": tokenize_data.attributes[0].raw,
                "attribute": {
                    "id": tokenize_data.attributes[0].attribute.id,
                    "name": tokenize_data.attributes[0].attribute.name,
                },
                "tokens": tokens,
            }
        )

    data = {
        "recordId": record_id,
        "attributes": attributes,
    }

    return pack_json_result({"data": {"tokenizeRecord": data}})


@router.delete("/{project_id}/record-label-association-by-ids")
async def delete_record_label_association_by_ids(request: Request, project_id: str):
    try:
        body = await request.json()
        record_id = body.get("recordId", "")
        association_ids = body.get("associationIds", [])
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"message": "Invalid JSON"},
        )

    user = auth_manager.get_user_by_info(request.state.info)
    rla_manager.delete_record_label_association(
        project_id, record_id, association_ids, user.id
    )

    return pack_json_result({"data": {"deleteRecordLabelAssociation": True}})


@router.delete("/{project_id}/{record_id}/record-by-id")
async def delete_record_by_id(request: Request, project_id: str, record_id: str):
    record_manager.delete_record(project_id, record_id)
    notification.send_organization_update(project_id, f"record_deleted:{record_id}")
    return pack_json_result({"data": {"deleteRecord": True}})


@router.post("/{project_id}/link-locked")
async def get_link_locked(
    request: Request, project_id: str, linkRouteBody: LinkRouteBody = Body(...)
):
    is_locked = manager.check_link_locked(project_id, linkRouteBody.link_route)
    return pack_json_result({"data": {"linkLocked": is_locked}})


@router.post("/{project_id}/generate-access-link")
def generate_access_link(
    request: Request,
    project_id: str,
    generateAccessLinkBody: GenerateAccessLinkBody = Body(...),
):

    user = auth_manager.get_user_by_info(request.state.info)

    try:
        link_type_parsed = enums.LinkTypes[generateAccessLinkBody.type.upper()]
    except KeyError:
        raise ValueError(f"Invalid LinkTypes: {generateAccessLinkBody.type}")

    if link_type_parsed == enums.LinkTypes.HEURISTIC:
        link = manager.generate_heuristic_access_link(
            project_id, user.id, generateAccessLinkBody.id
        )
    elif link_type_parsed == enums.LinkTypes.DATA_SLICE:
        print("not yet supported")
    notification.send_organization_update(
        project_id, f"access_link_created:{str(link.id)}"
    )

    data = {
        "link": {
            "id": str(link.id),
            "link": link.link,
            "isLocked": link.is_locked,
        }
    }

    return pack_json_result({"data": {"generateAccessLink": data}})
