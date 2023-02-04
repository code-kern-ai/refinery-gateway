import logging
from starlette.endpoints import HTTPEndpoint
from starlette.responses import JSONResponse

from controller.auth import manager as auth_manager
from controller.project import manager as project_manager
from controller.attribute import manager as attribute_manager
from submodules.model import exceptions

import os
from controller.tokenization import tokenization_service
from submodules.model import enums, events
from submodules.s3.controller import bucket_exists, create_bucket
from util import doc_ock, notification
from controller.transfer.record_transfer_manager import import_records_and_rlas
from controller.transfer.manager import check_and_add_running_id
from controller.auth import manager as auth_manager
from controller.project import manager as project_manager
from controller.upload_task import manager as upload_task_manager
from submodules.model import enums
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

__engine = None


def get_workflow_db_engine():
    global __engine
    if __engine is None:
        __engine = create_engine(os.getenv("WORKFLOW_POSTGRES"))
    return __engine


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
                }
                for attribute in attributes
            ],
            "knowledge_base_ids": [str(list.id) for list in project.knowledge_bases],
        }
        return JSONResponse(result)


class ProjectCreationFromWorkflow(HTTPEndpoint):
    async def post(self, request) -> JSONResponse:
        user_id = request.query_params["user_id"]
        request_body = await request.json()
        name = request_body["name"]
        description = request_body["description"]
        tokenizer = request_body["tokenizer"]
        store_id = request_body["store_id"]

        user = auth_manager.get_user_by_id(user_id)
        organization = auth_manager.get_organization_by_user_id(user.id)

        if not bucket_exists(str(organization.id)):
            create_bucket(str(organization.id))

        project = project_manager.create_project(
            organization.id, name, description, user.id
        )
        project_manager.update_project(project_id=project.id, tokenizer=tokenizer)

        Session = sessionmaker(get_workflow_db_engine())
        with Session() as session:
            results = session.execute(
                f"SELECT record FROM store_entry WHERE store_id = '{store_id}'"
            ).all()

        data = [result for result, in results]

        upload_task = upload_task_manager.create_upload_task(
            user_id=user.id,
            project_id=project.id,
            file_name=name,
            file_type="json",
            file_import_options="",
            upload_type=enums.UploadTypes.WORKFLOW_STORE.value,
        )
        import_records_and_rlas(
            project.id,
            user.id,
            data,
            upload_task,
            enums.RecordCategory.SCALE.value,
        )
        check_and_add_running_id(project.id, user.id)

        upload_task_manager.update_upload_task_to_finished(upload_task)
        tokenization_service.request_tokenize_project(str(project.id), str(user.id))

        notification.send_organization_update(
            project.id, f"project_created:{str(project.id)}", True
        )
        doc_ock.post_event(
            user,
            events.CreateProject(Name=f"{name}-{project.id}", Description=description),
        )

        return JSONResponse({"project_id": str(project.id)})
