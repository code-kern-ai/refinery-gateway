from fast_api.routes.client_response import pack_json_result
from fastapi import APIRouter, Request
from controller.information_source import manager
from submodules.model.business_objects import weak_supervision
from controller.auth import manager as auth_manager
from controller.organization import manager as org_manager
from submodules.model.business_objects.information_source import (
    get_heuristic_id_with_payload,
    get_source_statistics,
)
from submodules.model.util import pack_as_graphql, sql_alchemy_to_dict


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
    data = sql_alchemy_to_dict(get_heuristic_id_with_payload(project_id, heuristic_id))
    statistics = pack_as_graphql(
        sql_alchemy_to_dict(get_source_statistics(project_id, heuristic_id)),
        "sourceStatistics",
    )
    if statistics is not None:
        data["sourceStatistics"] = statistics["data"]["sourceStatistics"]
    return pack_json_result({"data": {"informationSourceBySourceId": data}})
