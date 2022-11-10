import logging
from starlette.endpoints import HTTPEndpoint
from starlette.responses import JSONResponse

from controller.auth import manager as auth_manager
from controller.project import manager as project_manager
from controller.attribute import manager as attribute_manager
from submodules.model import exceptions
from controller.embedding import manager as embedding_manager
from controller.information_source import manager as information_source_manager


logging.basicConfig(level=logging.DEBUG)


class ProjectSettings(HTTPEndpoint):
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
        attributes = attribute_manager.get_all_attributes(project_id, ["ALL"])
        result = {
            "name": project.name,
            "description": project.description,
            "tokenizer": project.tokenizer,
            "attributes": [
                {
                    "name": attribute.name,
                    "data_type": attribute.data_type,
                    "is_primary_key": attribute.is_primary_key,
                    "state": attribute.state,
                    "source_code": attribute.source_code,
                    "checked": attribute.is_selected_for_inference,
                }
                for attribute in attributes
            ],
            "embedders": [
                {
                    "name": embedder.name,
                    "checked": embedder.is_selected_for_inference,
                }
                for embedder in project.embeddings
            ],
            "tasks": [
                {
                    "name": task.name,
                    "type": task.task_type,
                    "heuristics": [
                        {
                            "name": heuristic.name,
                            "description": heuristic.description,
                            "type": heuristic.type,
                            "checked": heuristic.is_selected_for_inference,
                        }
                        for heuristic in task.information_sources
                    ],
                }
                for task in project.labeling_tasks
            ],
            "knowledge_base_ids": [str(list.id) for list in project.knowledge_bases],
        }
        return JSONResponse(result)

    async def put(self, request) -> JSONResponse:
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

        data = await request.json()

        attributes = data["attributeCalculationsSelected"]
        embeddings = data["embeddersSelected"]
        information_sources = data["heuristicsSelected"]

        attribute_ids_selected = []

        embedding_ids_selected = []
        for embedding_name in embeddings:
            embedding = embedding_manager.get_embedding_by_name(
                project_id, embedding_name
            )
            embedding_ids_selected.append(embedding.id)

        heuristic_ids_selected = []
        for information_source_name in information_sources:
            heuristic = information_source_manager.get_information_source_by_name(
                project_id, information_source_name
            )
            heuristic_ids_selected.append(heuristic.id)

        project_manager.update_inference_settings(
            project_id,
            attribute_ids_selected,
            embedding_ids_selected,
            heuristic_ids_selected,
        )

        return JSONResponse({"success": True})
