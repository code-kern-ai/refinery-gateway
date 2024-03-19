from fastapi import APIRouter, Request
from fast_api.routes.client_response import pack_json_result
from typing import Dict
from controller.auth import manager as auth_manager
from fast_api.routes.fastapi_resolve_info import FastAPIResolveInfo
from submodules.model.business_objects.project import get_project_by_project_id_sql
from controller.project import manager
from submodules.model.util import sql_alchemy_to_dict, pack_as_graphql

router = APIRouter()


@router.get("/project-by-project-id/{project_id}")
async def get_project_by_project_id(request: Request, project_id: str) -> Dict:
    info = FastAPIResolveInfo(
        context={"request": request},
        field_name="ProjectQuery",
        parent_type="Query",
    )

    auth_manager.check_demo_access(info)
    auth_manager.check_project_access(info, project_id)

    data = get_project_by_project_id_sql(project_id)

    return pack_json_result({"data": {"projectByProjectId": data}})


@router.get("/all-projects")
async def get_all_projects(request: Request, userId: str) -> Dict:
    info = FastAPIResolveInfo(
        context={"request": request},
        field_name="ProjectQuery",
        parent_type="Query",
    )

    auth_manager.check_demo_access(info)
    organization = auth_manager.get_organization_id_by_info(info)

    projects = manager.get_all_projects_by_user(organization.id)
    projects_graphql = pack_as_graphql(projects, "allProjects")
    return pack_json_result(projects_graphql)
