import logging
import traceback

from controller import organization
from starlette.endpoints import HTTPEndpoint
from starlette.responses import PlainTextResponse, JSONResponse
from submodules.s3 import controller as s3
from submodules.model.business_objects import organization

from controller.transfer import manager as upload_manager
from controller.upload_task import manager as task_manager
from controller.auth import manager as auth_manager
from controller.transfer import manager as transfer_manager
from controller.auth import manager as auth

from submodules.model import enums
from util.notification import create_notification
from submodules.model.enums import NotificationType
from submodules.model.models import UploadTask
from submodules.model.business_objects import general
from util import notification
from controller.tokenization import tokenization_service

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Notify(HTTPEndpoint):
    async def post(self, request) -> PlainTextResponse:
        auth.check_is_demo_without_info()
        data = await request.json()
        file_path = data["Key"]

        if len(file_path.split("/")) != 4:
            # We need handling for lf execution notification here.
            # ATM we have a different path of handling in util/payload_scheduler.py update_records method
            return PlainTextResponse("OK")

        org_id, project_id, upload_task_id, file_name = file_path.split("/")
        if len(project_id) != 36:
            return PlainTextResponse("OK")
        if upload_task_id == "download":
            return PlainTextResponse("OK")
        if org_id == "archive":
            return PlainTextResponse("OK")

        task = task_manager.get_upload_task_secure(
            upload_task_id=upload_task_id,
            project_id=project_id,
            file_name=file_name,
        )
        is_global_update = True if task.file_type == "project" else False
        try:
            init_file_import(task, project_id, is_global_update)
        except Exception:
            file_import_error_handling(task, project_id, is_global_update)
        notification.send_organization_update(project_id, "project_update", True)
        return PlainTextResponse("OK")


class FileExport(HTTPEndpoint):
    def get(self, request) -> JSONResponse:
        project_id = request.path_params["project_id"]
        user_id = request.query_params["user_id"]
        num_samples = request.query_params.get("num_samples")
        auth_manager.check_project_access_from_user_id(user_id, project_id)
        result = transfer_manager.export_records(project_id, num_samples)
        return JSONResponse(result)


class KnowledgeBaseExport(HTTPEndpoint):
    def get(self, request) -> JSONResponse:
        project_id = request.path_params["project_id"]
        list_id = request.path_params["knowledge_base_id"]
        user_id = request.query_params["user_id"]
        auth_manager.check_project_access_from_user_id(user_id, project_id)
        result = transfer_manager.export_knowledge_base(project_id, list_id)
        return JSONResponse(result)


class PrepareImport(HTTPEndpoint):
    async def post(self, request) -> JSONResponse:
        auth.check_is_demo_without_info()
        project_id = request.path_params["project_id"]
        request_body = await request.json()

        user_id = request_body["user_id"]
        auth_manager.check_project_access_from_user_id(user_id, project_id)
        file_name = request_body["file_name"]
        file_type = request_body["file_type"]
        file_import_options = request_body.get("file_import_options")
        task = task_manager.create_upload_task(
            user_id, project_id, file_name, file_type, file_import_options
        )
        org_id = organization.get_id_by_project_id(project_id)
        credentials_and_id = s3.get_upload_credentials_and_id(
            org_id, f"{project_id}/{task.id}"
        )
        return JSONResponse(credentials_and_id)


class UploadTask(HTTPEndpoint):
    def get(self, request) -> JSONResponse:
        auth.check_is_demo_without_info()
        project_id = request.path_params["project_id"]
        task_id = request.path_params["task_id"]
        user_id = request.query_params["user_id"]
        auth_manager.check_project_access_from_user_id(user_id, project_id)
        task = task_manager.get_upload_task(project_id, task_id)
        task_dict = {
            "id": str(task.id),
            "file_name": str(task.file_name),
            "file_type": str(task.file_type),
            "progress": task.progress,
            "state": str(task.state),
            "started_at": str(task.started_at),
        }
        return JSONResponse(task_dict)


def init_file_import(task: UploadTask, project_id: str, is_global_update: bool) -> None:
    if "records" in task.file_type:
        upload_manager.import_records(project_id, task)
    elif "project" in task.file_type:
        upload_manager.import_project(project_id, task)
    elif "knowledge_base" in task.file_type:
        upload_manager.import_knowledge_base(project_id, task)

    notification.send_organization_update(
        project_id, f"file_upload:{str(task.id)}:state:{task.state}", is_global_update
    )
    if task.file_type != "knowledge_base":
        tokenization_service.request_tokenize_project(project_id, str(task.user_id))


def file_import_error_handling(
    task: UploadTask, project_id: str, is_global_update: bool
) -> None:
    general.rollback()
    task.state = enums.UploadStates.ERROR.value
    general.commit()
    create_notification(
        NotificationType.IMPORT_FAILED,
        task.user_id,
        task.project_id,
        task.file_type,
    )
    logger.error(
        task_manager.get_upload_task_message(
            task,
        )
    )
    print(traceback.format_exc(), flush=True)
    notification.send_organization_update(
        project_id, f"file_upload:{str(task.id)}:state:{task.state}", is_global_update
    )
