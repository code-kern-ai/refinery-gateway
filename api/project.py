import logging
from starlette.endpoints import HTTPEndpoint
from starlette.responses import JSONResponse

from controller.auth import manager as auth_manager
from controller.project import manager as project_manager
from controller.attribute import manager as attribute_manager
from submodules.model import exceptions


logging.basicConfig(level=logging.DEBUG)


class ProjectDetails(HTTPEndpoint):
    def get(self, request) -> JSONResponse:
        project_id = request.path_params["project_id"]
        user_id = request.query_params["user_id"]
        try:
            auth_manager.check_project_access_from_user_id(
                user_id, project_id, from_api=True
            )
        except exceptions.EntityNotFoundException:
            return JSONResponse({"error": "Could not find project"}, status_code=404)
        except exceptions.AccessDeniedException:
            return JSONResponse({"error": "Access denied"}, status_code=403)
        project = project_manager.get_project(project_id)
        attributes = attribute_manager.get_all_attributes(project_id)
        result = {
            "name": project.name,
            "description": project.description,
            "tokenizer": project.tokenizer,
            "attributes": [
                {
                    "name": attribute.name,
                    "data_type": attribute.data_type,
                    "is_primary_key": attribute.is_primary_key,
                }
                for attribute in attributes
            ],
            "knowledge_base_ids": [str(list.id) for list in project.knowledge_bases],
        }
        return JSONResponse(result)
