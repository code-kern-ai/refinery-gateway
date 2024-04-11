import json
from controller.auth import manager as auth_manager
from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import JSONResponse
from fast_api.models import (
    AddClassificationLabelBody,
    AddExtractionLabelBody,
    CreateLabelingTaskBody,
    GenerateAccessLinkBody,
    LinkRouteBody,
    LockAccessLinkBody,
    RemoveGoldStarBody,
    SetGoldStarBody,
    StringBody,
    TokenizedRecordBody,
    UpdateLabelColorBody,
    UpdateLabelHotkeyBody,
    UpdateLabelNameBody,
    UpdateLabelingTaskBody,
    WarningDataBody,
)
from submodules.model import enums, events
from fast_api.routes.client_response import pack_json_result
from controller.labeling_access_link import manager
from controller.labeling_task import manager as labeling_manager
from controller.labeling_task_label import manager as label_manager
from controller.labeling_task import manager as task_manager
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
from util import doc_ock, notification


router = APIRouter()

AVAILABLE_LINKS_WHITELIST = ["id", "link", "link_type", "name", "is_locked"]


@router.post(
    "/{project_id}/available-links",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
async def get_available_links(
    request: Request,
    project_id: str,
):
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


@router.post(
    "/{project_id}/huddle-data",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
async def get_huddle_data(
    request: Request,
    project_id: str,
):
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
async def get_tokenized_record(request: Request, body: TokenizedRecordBody = Body(...)):
    record_item = record.get_without_project_id(body.record_id)
    if not record_item:
        return pack_json_result({"data": {"tokenizeRecord": None}})

    # specific scenario where we should not delegate this call up to middleware
    auth_manager.check_project_access(request.state.info, record_item.project_id)

    tokenize_data = tokenization_manager.get_tokenized_record(
        record_item.project_id, body.record_id
    )

    attributes = []

    for attr in tokenize_data.attributes:
        tokens = None
        if attr.tokens is not None:
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
                    "id": str(tokenize_data.attributes[0].attribute.id),
                    "name": tokenize_data.attributes[0].attribute.name,
                },
                "tokens": tokens,
            }
        )

    data = {
        "recordId": body.record_id,
        "attributes": attributes,
    }

    return pack_json_result({"data": {"tokenizeRecord": data}})


@router.delete(
    "/{project_id}/record-label-association-by-ids",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
async def delete_record_label_association_by_ids(
    request: Request,
    project_id: str,
):
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

    return pack_json_result({"data": {"deleteRecordLabelAssociation": {"ok": True}}})


@router.delete(
    "/{project_id}/{record_id}/record-by-id",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
async def delete_record_by_id(
    request: Request,
    project_id: str,
    record_id: str,
):
    record_manager.delete_record(project_id, record_id)
    notification.send_organization_update(project_id, f"record_deleted:{record_id}")
    return pack_json_result({"data": {"deleteRecord": {"ok": True}}})


@router.post(
    "/{project_id}/link-locked",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
async def get_link_locked(
    request: Request,
    project_id: str,
    linkRouteBody: LinkRouteBody = Body(...),
):
    is_locked = manager.check_link_locked(project_id, linkRouteBody.link_route)
    return pack_json_result({"data": {"linkLocked": is_locked}})


@router.post(
    "/{project_id}/generate-access-link",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
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


@router.delete(
    "/{project_id}/remove-access-link",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def remove_access_link(
    request: Request,
    project_id: str,
    stringBody: StringBody = Body(...),
):

    type_id = manager.remove(stringBody.value)
    notification.send_organization_update(
        project_id, f"access_link_removed:{stringBody.value}:{type_id}"
    )

    data = {"ok": True}

    return pack_json_result({"data": {"removeAccessLink": data}})


@router.put(
    "/{project_id}/lock-access-link",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def lock_access_link(
    request: Request,
    project_id: str,
    lockAccessLinkBody: LockAccessLinkBody = Body(...),
):
    type_id = manager.change_user_access_to_link_lock(
        lockAccessLinkBody.link_id, lockAccessLinkBody.lock_state
    )
    notification.send_organization_update(
        project_id,
        f"access_link_changed:{lockAccessLinkBody.link_id}:{type_id}:{lockAccessLinkBody.lock_state}",
    )

    data = {"ok": True}

    return pack_json_result({"data": {"lockAccessLink": data}})


@router.post(
    "/{project_id}/add-classification-labels",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def add_classification_labels_to_record(
    request: Request, project_id: str, body: AddClassificationLabelBody = Body(...)
):
    user = auth_manager.get_user_by_info(request.state.info)
    rla_manager.create_manual_classification_label(
        project_id,
        user.id,
        body.record_id,
        body.label_id,
        body.labeling_task_id,
        body.as_gold_star,
        body.source_id,
    )

    # this below seems not optimal positioned here
    project = project_manager.get_project(project_id)
    doc_ock.post_event(
        str(user.id),
        events.AddLabelsToRecord(
            ProjectName=f"{project.name}-{project.id}",
            Type=enums.LabelingTaskType.CLASSIFICATION.value,
        ),
    )
    notification.send_organization_update(project_id, f"rla_created:{body.record_id}")
    return pack_json_result({"data": {"addClassificationLabelsToRecord": {"ok": True}}})


@router.post(
    "/{project_id}/add-extraction-label",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def add_extraction_label_to_record(
    request: Request, project_id: str, body: AddExtractionLabelBody = Body(...)
):
    user = auth_manager.get_user_by_info(request.state.info)
    rla_manager.create_manual_extraction_label(
        project_id,
        user.id,
        body.record_id,
        body.labeling_task_id,
        body.label_id,
        body.token_start_index,
        body.token_end_index,
        body.value,
        body.as_gold_star,
        body.source_id,
    )
    project = project_manager.get_project(project_id)
    doc_ock.post_event(
        str(user.id),
        events.AddLabelsToRecord(
            ProjectName=f"{project.name}-{project.id}",
            Type=enums.LabelingTaskType.INFORMATION_EXTRACTION.value,
        ),
    )
    notification.send_organization_update(project_id, f"rla_created:{body.record_id}")
    return pack_json_result({"data": {"addExtractionLabelToRecord": {"ok": True}}})


@router.post(
    "/{project_id}/set-gold-star",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def set_gold_star(request: Request, project_id: str, body: SetGoldStarBody = Body(...)):
    user = auth_manager.get_user_by_info(request.state.info)
    task_type = rla_manager.create_gold_star_association(
        project_id, body.record_id, body.labeling_task_id, body.gold_user_id, user.id
    )

    project = project_manager.get_project(project_id)
    doc_ock.post_event(
        str(user.id),
        events.AddLabelsToRecord(
            ProjectName=f"{project.name}-{project.id}",
            Type=task_type,
        ),
    )
    notification.send_organization_update(project_id, f"rla_created:{body.record_id}")
    return pack_json_result({"data": {"setGoldStarAnnotationForTask": {"ok": True}}})


@router.post(
    "/{project_id}/remove-gold-star",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def remove_gold_star(
    request: Request, project_id: str, body: RemoveGoldStarBody = Body(...)
):
    user = auth_manager.get_user_by_info(request.state.info)
    rla_manager.delete_gold_star_association(
        project_id, user.id, body.record_id, body.labeling_task_id
    )
    notification.send_organization_update(project_id, f"rla_deleted:{body.record_id}")
    return pack_json_result({"data": {"removeGoldStarAnnotationForTask": {"ok": True}}})


@router.put(
    "/{project_id}/update-labeling-task",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def update_labeling_task(project_id: str, body: UpdateLabelingTaskBody = Body(...)):
    labeling_manager.update_labeling_task(
        project_id,
        body.labeling_task_id,
        body.labeling_task_target_id,
        body.labeling_task_name,
        body.labeling_task_type,
    )

    notification.send_organization_update(
        project_id,
        f"labeling_task_updated:{body.labeling_task_id}:{body.labeling_task_type}",
    )

    return pack_json_result({"data": {"updateLabelingTask": {"ok": True}}})


@router.delete(
    "/{project_id}/delete-labeling-task",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def delete_labeling_task(project_id: str, body: StringBody = Body(...)):
    labeling_task_id = body.value
    labeling_manager.delete_labeling_task(project_id, labeling_task_id)

    notification.send_organization_update(
        project_id, f"labeling_task_deleted:{labeling_task_id}"
    )

    return pack_json_result({"data": {"deleteLabelingTask": {"ok": True}}})


@router.post(
    "/{project_id}/create-labeling-task",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def create_labeling_task(
    project_id: str, request: Request, body: CreateLabelingTaskBody = Body(...)
):
    user = auth_manager.get_user_by_info(request.state.info)
    project = project_manager.get_project(project_id)

    item = labeling_manager.create_labeling_task(
        project_id,
        body.labeling_task_name,
        body.labeling_task_type,
        body.labeling_task_target_id,
    )

    doc_ock.post_event(
        str(user.id),
        events.AddLabelingTask(
            ProjectName=f"{project.name}-{project.id}",
            Name=body.labeling_task_name,
            Type=body.labeling_task_type,
        ),
    )

    notification.send_organization_update(
        project_id, f"labeling_task_created:{str(item.id)}"
    )

    return pack_json_result({"data": {"createLabelingTask": {"ok": True}}})


@router.delete(
    "/{project_id}/delete-label",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def delete_label(project_id: str, body: StringBody = Body(...)):
    label_id = body.value
    label = label_manager.get_label(project_id, body.value)
    labeling_task_id = str(label.labeling_task_id)
    label_manager.delete_label(project_id, label_id)
    notification.send_organization_update(
        project_id, f"label_deleted:{label_id}:labeling_task:{labeling_task_id}"
    )

    return pack_json_result({"data": {"deleteLabel": {"ok": True}}})


@router.post(
    "/{project_id}/create-label",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
async def create_label(
    request: Request,
    project_id: str,
):
    try:
        body = await request.json()
        label_name = body.get("labelName")
        labeling_task_id = body.get("labelingTaskId")
        label_color = body.get("labelColor")
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"message": "Invalid JSON"},
        )

    if project_id:
        auth_manager.check_project_access(request.state.info, project_id)

    user = auth_manager.get_user_by_info(request.state.info)
    label = label_manager.create_label(
        project_id, label_name, labeling_task_id, label_color
    )
    task = task_manager.get_labeling_task(project_id, labeling_task_id)
    project = project_manager.get_project(project_id)
    doc_ock.post_event(
        str(user.id),
        events.AddLabel(
            ProjectName=f"{project.name}-{project.id}",
            Name=label_name,
            LabelingTaskName=task.name,
        ),
    )
    notification.send_organization_update(
        project_id, f"label_created:{label.id}:labeling_task:{labeling_task_id}"
    )
    return pack_json_result({"data": {"createLabel": {"ok": True}}})


@router.put(
    "/{project_id}/update-label-color",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def update_label_color(project_id: str, body: UpdateLabelColorBody = Body(...)):
    label_manager.update_label_color(
        project_id, body.labeling_task_label_id, body.label_color
    )
    return pack_json_result({"data": {"updateLabelColor": {"ok": True}}})


@router.put(
    "/{project_id}/update-label-hotkey",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def update_label_hotkey(project_id: str, body: UpdateLabelHotkeyBody = Body(...)):
    label_manager.update_label_hotkey(
        project_id, body.labeling_task_label_id, body.label_hotkey
    )
    return pack_json_result({"data": {"updateLabelHotkey": {"ok": True}}})


@router.post(
    "/{project_id}/handle-label-rename-warnings",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def handle_label_rename_warnings(
    project_id: str,
    body: WarningDataBody = Body(...),
):
    label_manager.handle_label_rename_warning(project_id, body.warning_data)
    return pack_json_result({"data": {"handleLabelRenameWarnings": {"ok": True}}})


@router.put(
    "/{project_id}/update-label-name",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def update_label_name(
    project_id: str,
    body: UpdateLabelNameBody = Body(...),
):
    label_manager.update_label_name(project_id, body.label_id, body.new_name)
    return pack_json_result({"data": {"updateLabelName": {"ok": True}}})
