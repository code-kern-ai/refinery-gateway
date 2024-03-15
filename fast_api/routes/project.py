from fastapi import APIRouter, Request
from fast_api.routes.client_response import pack_json_result
from typing import Dict
from controller.auth import manager as auth
from submodules.model.business_objects.project import get_project_by_project_id_sql


router = APIRouter()


@router.get("/project-by-project-id/{project_id}")
async def get_project_by_project_id(request: Request, project_id: str) -> Dict:

    # auth.check_demo_access(info)
    # auth.check_project_access(info, project_id)

    data = get_project_by_project_id_sql(project_id)

    return pack_json_result({"data": {"projectByProjectId": data}})
