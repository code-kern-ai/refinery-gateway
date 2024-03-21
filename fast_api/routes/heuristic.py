from fast_api.routes.client_response import pack_json_result
from fastapi import APIRouter, Request
from controller.information_source import manager


router = APIRouter()


@router.get("/{project_id}/information-sources-overview-data")
def get_information_sources_overview_data(request: Request, project_id: str):
    data = manager.get_overview_data(project_id)
    return pack_json_result({"data": {"informationSourcesOverviewData": data}})
