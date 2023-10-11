import logging
from starlette.endpoints import HTTPEndpoint
from starlette.responses import JSONResponse

from controller.auth import manager as auth_manager
from controller.project import manager as project_manager
from controller.attribute import manager as attribute_manager
from submodules.model import exceptions

from controller.tokenization import tokenization_service
from submodules.model import events
from submodules.s3.controller import bucket_exists, create_bucket
from util import doc_ock, notification, adapter

from controller.task_queue import manager as task_queue_manager
from submodules.model.enums import TaskType, RecordTokenizationScope

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
        max_running_id = project_manager.get_max_running_id(project_id)
        attributes = attribute_manager.get_all_attributes(project_id, ["ALL"])
        result = {
            "name": project.name,
            "max_running_id": max_running_id,
            "description": project.description,
            "tokenizer": project.tokenizer,
            "attributes": [
                {
                    "name": attribute.name,
                    "data_type": attribute.data_type,
                    "is_primary_key": attribute.is_primary_key,
                    "state": attribute.state,
                }
                for attribute in attributes
            ],
            "knowledge_base_ids": [str(list.id) for list in project.knowledge_bases],
        }
        return JSONResponse(result)


class ProjectCreationFromWorkflow(HTTPEndpoint):
    async def post(self, request_body) -> JSONResponse:
        (
            user_id,
            name,
            description,
            tokenizer,
            store_id,
        ) = await adapter.unpack_request_body(request_body)

        user = auth_manager.get_user_by_id(user_id)
        organization = auth_manager.get_organization_by_user_id(user.id)

        if not bucket_exists(str(organization.id)):
            create_bucket(str(organization.id))

        project = project_manager.create_project(
            organization.id, name, description, user.id
        )
        project_manager.update_project(project_id=project.id, tokenizer=tokenizer)
        data = adapter.get_records_from_store(store_id)
        adapter.check(data, project.id, user.id)

        project_manager.add_workflow_store_data_to_project(
            user_id=user.id, project_id=project.id, file_name=name, data=data
        )

        task_queue_manager.add_task(
            str(project.id),
            TaskType.TOKENIZATION,
            str(user.id),
            {
                "scope": RecordTokenizationScope.PROJECT.value,
                "include_rats": True,
                "only_uploaded_attributes": False,
            },
        )

        notification.send_organization_update(
            project.id, f"project_created:{str(project.id)}", True
        )
        doc_ock.post_event(
            str(user.id),
            events.CreateProject(Name=f"{name}-{project.id}", Description=description),
        )

        return JSONResponse({"project_id": str(project.id)})
