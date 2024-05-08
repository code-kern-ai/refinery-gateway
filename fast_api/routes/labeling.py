import json
from controller.auth import manager as auth_manager
from fastapi import APIRouter, Body, Depends, Request
from fast_api.models import (
    AddClassificationLabelBody,
    AddExtractionLabelBody,
    AvailableLinksBody,
    DeleteRecordLabelAssociationBody,
    GenerateAccessLinkBody,
    HuddleDataBody,
    LinkRouteBody,
    LockAccessLinkBody,
    RemoveGoldStarBody,
    SetGoldStarBody,
    StringBody,
    TokenizedRecordBody,
)
from submodules.model import enums, events
from fast_api.routes.client_response import pack_json_result
from controller.labeling_access_link import manager
from controller.labeling_task_label import manager as label_manager
from controller.labeling_task import manager as task_manager
from controller.project import manager as project_manager
from submodules.model.business_objects import record
from controller.tokenization import manager as tokenization_manager
from controller.attribute import manager as attribute_manager
from controller.information_source import manager as information_source_manager

from controller.record_label_association import manager as rla_manager
from controller.record import manager as record_manager
from submodules.model.business_objects import (
    information_source as information_source,
    user as user_manager,
    data_slice,
)
from submodules.model.util import sql_alchemy_to_dict, to_frontend_obj_raw
from util import doc_ock, notification
from controller.auth import kratos


router = APIRouter()

AVAILABLE_LINKS_WHITELIST = ["id", "link", "link_type", "name", "is_locked"]


@router.post(
    "/{project_id}/available-links",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_available_links(
    request: Request,
    project_id: str,
    body: AvailableLinksBody = Body(...),
):
    assumed_role = body.assumedRole
    assumed_heuristic_id = body.assumedHeuristicId

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
def get_huddle_data(
    request: Request,
    project_id: str,
    body: HuddleDataBody = Body(...),
):
    huddle_id = body.huddleId
    huddle_type = body.huddleType

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
def get_tokenized_record(request: Request, body: TokenizedRecordBody = Body(...)):
    record_item = record.get_without_project_id(body.record_id)
    if not record_item:
        return pack_json_result({"data": {"tokenizeRecord": None}})

    # Delegated here due to record_item dep
    auth_manager.check_project_access(request.state.info, record_item.project_id)

    tokenize_data = tokenization_manager.get_tokenized_record(
        record_item.project_id, body.record_id
    )

    attributes = []

    for attr in tokenize_data["attributes"]:
        tokens = None
        if attr["tokens"] is not None:
            tokens = [
                {
                    "value": token["value"],
                    "idx": token["idx"],
                    "posStart": token["pos_start"],
                    "posEnd": token["pos_end"],
                    "type": token["type"],
                }
                for token in attr["tokens"]
            ]
        attributes.append(
            {
                "raw": tokenize_data["attributes"][0]["raw"],
                "attribute": {
                    "id": str(tokenize_data["attributes"][0]["attribute"].id),
                    "name": tokenize_data["attributes"][0]["attribute"].name,
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
def delete_record_label_association_by_ids(
    request: Request,
    project_id: str,
    body: DeleteRecordLabelAssociationBody = Body(...),
):
    record_id = body.recordId
    association_ids = body.associationIds

    user = auth_manager.get_user_by_info(request.state.info)
    rla_manager.delete_record_label_association(
        project_id, record_id, association_ids, user.id
    )

    return pack_json_result({"data": {"deleteRecordLabelAssociation": {"ok": True}}})


@router.delete(
    "/{project_id}/{record_id}/record-by-id",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def delete_record_by_id(
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
def get_link_locked(
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


@router.get(
    "/{project_id}/record-label-associations",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_record_label_associations(
    request: Request,
    project_id: str,
    record_id: str,
):
    record = record_manager.get_record(project_id, record_id)

    user_id = auth_manager.get_user_id_by_info(request.state.info)
    names, mail = kratos.resolve_user_name_and_email_by_id(user_id)
    first_name = names.get("first", "")
    last_name = names.get("last", "")

    edges = []
    rla = record.record_label_associations
    for r in rla:

        source_id = getattr(r, "source_id", None)

        informationSourceDict = None
        labelingTaskLabelDict = {}
        labelingTaskDict = {}
        attributeDict = None

        token_start_idx = None
        token_end_idx = None

        if len(r.tokens) > 0:
            token_start_idx = r.tokens[0].token_index
            token_end_idx = r.tokens[-1].token_index

        if source_id:
            information_source = information_source_manager.get_information_source(
                project_id, source_id
            )
            if information_source:
                informationSourceDict = {
                    "type": information_source.type,
                    "return_type": information_source.return_type,
                    "name": information_source.name,
                    "description": information_source.description,
                    "createdAt": information_source.created_at,
                    "createdBy": information_source.created_by,
                }

        labelingTaskLabel = label_manager.get_label(
            project_id, str(r.labeling_task_label_id)
        )

        if labelingTaskLabel:
            labelingTaskLabelDict = {
                "id": str(labelingTaskLabel.id),
                "name": labelingTaskLabel.name,
                "color": labelingTaskLabel.color,
            }

            labelingTask = task_manager.get_labeling_task(
                project_id, labelingTaskLabel.labeling_task_id
            )
            if labelingTask:
                labelingTaskDict = {
                    "id": str(labelingTask.id),
                    "name": labelingTask.name,
                }
                labelingTaskLabelDict["labeling_task"] = labelingTaskDict

                attribute = attribute_manager.get_attribute(
                    project_id, labelingTask.attribute_id
                )
                if attribute:
                    attributeDict = {
                        "id": str(labelingTask.attribute_id),
                        "name": attribute.name,
                        "relative_position": attribute.relative_position,
                    }

                labelingTaskLabelDict["labeling_task"]["attribute"] = attributeDict
        edges.append(
            {
                "node": {
                    "id": str(r.id),
                    "recordId": str(r.record_id),
                    "labelingTaskLabelId": str(r.labeling_task_label_id),
                    "source_id": getattr(r, "source_id", None),
                    "source_type": r.source_type,
                    "return_type": r.return_type,
                    "confidence": getattr(r, "confidence", None),
                    "created_at": r.created_at,
                    "created_by": str(r.created_by),
                    "token_start_idx": token_start_idx,
                    "token_end_idx": token_end_idx,
                    "is_gold_star": getattr(r, "is_gold_star", None),
                    "user": {
                        "id": str(user_id),
                        "firstName": first_name,
                        "lastName": last_name,
                        "mail": mail,
                    },
                    "information_source": informationSourceDict,
                    "labeling_task_label": labelingTaskLabelDict,
                }
            }
        )

    data = {"id": str(record.id), "recordLabelAssociations": {"edges": edges}}

    return pack_json_result({"data": {"recordByRecordId": data}})
