from fast_api.models import CreateHeuristicBody, UpdateHeuristicBody
from fast_api.routes.client_response import pack_json_result
from fastapi import APIRouter, Body, Request
from controller.information_source import manager
from submodules.model.business_objects import weak_supervision
from controller.auth import manager as auth_manager
from controller.organization import manager as org_manager
from controller.labeling_access_link import manager as access_link_manager
from controller.payload import manager as payload_manager
from submodules.model.business_objects import information_source
from submodules.model.business_objects.payload import get_payload_with_heuristic_type
from submodules.model.enums import InformationSourceType
from submodules.model.util import pack_as_graphql, sql_alchemy_to_dict
from util import notification
from controller.task_queue import manager as task_queue_manager
from submodules.model import enums

router = APIRouter()


@router.get("/{project_id}/information-sources-overview-data")
def get_information_sources_overview_data(request: Request, project_id: str):
    data = manager.get_overview_data(project_id)
    return pack_json_result({"data": {"informationSourcesOverviewData": data}})


@router.get("/{project_id}/weak-supervision-run")
def get_weak_supervision_run(request: Request, project_id: str):
    if project_id:
        auth_manager.check_project_access(request.state.info, project_id)

    user = auth_manager.get_user_by_info(request.state.info)
    data = org_manager.get_user_info(user)
    ws_data = sql_alchemy_to_dict(
        weak_supervision.get_current_weak_supervision_run(project_id)
    )
    ws_data["user"] = data
    return pack_json_result({"data": {"currentWeakSupervisionRun": ws_data}})


@router.get("/{project_id}/{heuristic_id}/heuristic-by-id")
def get_heuristic_by_heuristic_id(project_id: str, heuristic_id: str):
    data = sql_alchemy_to_dict(
        information_source.get_heuristic_id_with_payload(project_id, heuristic_id)
    )
    statistics = pack_as_graphql(
        sql_alchemy_to_dict(
            information_source.get_source_statistics(project_id, heuristic_id)
        ),
        "sourceStatistics",
    )
    if statistics is not None:
        data["sourceStatistics"] = statistics["data"]["sourceStatistics"]
    return pack_json_result({"data": {"informationSourceBySourceId": data}})


@router.get("/{project_id}/{payload_id}/payload-by-id")
def get_payload_by_payload_id(project_id: str, payload_id: str):
    data = sql_alchemy_to_dict(get_payload_with_heuristic_type(project_id, payload_id))
    return pack_json_result({"data": {"payloadByPayloadId": data}})


@router.get("/{project_id}/{heuristic_id}/lf-on-10-records")
def get_labeling_function_on_10_records(project_id: str, heuristic_id: str):
    data = sql_alchemy_to_dict(
        payload_manager.get_labeling_function_on_10_records(project_id, heuristic_id)
    )
    records = []
    for record in data.records:
        records.append(
            {
                "recordId": record.record_id,
                "calculatedLabels": record.calculated_labels,
                "fullRecordData": record.full_record_data,
            }
        )
    final_data = {
        "records": records,
        "containerLogs": data.container_logs,
        "codeHasErrors": data.code_has_errors,
    }
    return {"data": {"getLabelingFunctionOn10Records": final_data}}


@router.get("/{project_id}/model-callbacks-overview-data")
def get_model_callbacks_overview_data(request: Request, project_id: str):
    data = manager.get_overview_data(project_id, is_model_callback=True)
    return pack_json_result({"data": {"modelCallbacksOverviewData": data}})


@router.get("/{project_id}/access-link")
def get_access_link(request: Request, project_id: str, link_id: str):
    accessLink = access_link_manager.get(link_id)

    data = {
        "id": str(accessLink.id),
        "link": accessLink.link,
        "isLocked": accessLink.is_locked,
    }

    return pack_json_result({"data": {"accessLink": data}})


@router.post("/{project_id}/{information_source_id}/toggle-heuristic")
def toggle_heuristic(request: Request, project_id: str, information_source_id: str):
    manager.toggle_information_source(project_id, information_source_id)
    notification.send_organization_update(
        project_id, f"information_source_updated:{information_source_id}"
    )
    return pack_json_result({"data": {"toggleInformationSource": {"ok": True}}})


@router.post("/{project_id}")
def set_information_sources(request: Request, project_id: str, value: bool):
    manager.set_all_information_source_selected(project_id, value)
    notification.send_organization_update(project_id, "information_source_updated:all")
    return pack_json_result({"data": {"setAllInformationSources": {"ok": True}}})


@router.post("/{project_id}/{heuristic_id}/payload")
def set_payload(request: Request, project_id: str, heuristic_id: str):
    user = auth_manager.get_user_by_info(request.state.info)
    information_source_item = information_source.get(project_id, heuristic_id)
    if information_source_item.type == enums.InformationSourceType.CROWD_LABELER.value:
        return pack_json_result({"data": {"createPayload": None}})
    priority = (
        information_source_item.type != enums.InformationSourceType.ZERO_SHOT.value
    )

    queue_id, _ = task_queue_manager.add_task(
        project_id,
        enums.TaskType.INFORMATION_SOURCE,
        user.id,
        {
            "information_source_id": heuristic_id,
            "source_type": information_source_item.type,
        },
        priority=priority,
    )

    return pack_json_result({"data": {"createPayload": {"queueId": queue_id}}})


@router.delete("/{project_id}/{heuristic_id}/delete-heuristic")
def delete_heuristic(request: Request, project_id: str, heuristic_id: str):
    manager.delete_information_source(project_id, heuristic_id)
    notification.send_organization_update(
        project_id, f"information_source_deleted:{heuristic_id}"
    )
    return pack_json_result({"data": {"deleteInformationSource": {"ok": True}}})


@router.post("/{project_id}/create-heuristic")
def create_heuristic(
    request: Request, project_id: str, body: CreateHeuristicBody = Body(...)
):
    user = auth_manager.get_user_by_info(request.state.info)
    if body.type == InformationSourceType.CROWD_LABELER.value:
        information_source = manager.create_crowd_information_source(
            str(user.id), project_id, body.labeling_task_id, body.name, body.description
        )

    else:
        information_source = manager.create_information_source(
            project_id,
            user.id,
            body.labeling_task_id,
            body.name,
            body.source_code,
            body.description,
            body.type,
        )
    notification.send_organization_update(
        project_id, f"information_source_created:{str(information_source.id)}"
    )
    return {
        "data": {"createInformationSource": {"informationSource": information_source}}
    }


@router.post("/{project_id}/{heuristic_id}/update-heuristic")
def update_heuristic(
    request: Request,
    project_id: str,
    heuristic_id: str,
    body: UpdateHeuristicBody = Body(...),
):
    manager.update_information_source(
        project_id,
        heuristic_id,
        body.labeling_task_id,
        body.code,
        body.description,
        body.name,
    )
    user = auth_manager.get_user_by_info(request.state.info)
    notification.send_organization_update(
        project_id, f"information_source_updated:{heuristic_id}:{user.id}"
    )
    return {"data": {"updateInformationSource": {"ok": True}}}
