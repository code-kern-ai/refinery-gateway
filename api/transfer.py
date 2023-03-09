import logging
import traceback
import time

from controller import organization
from starlette.endpoints import HTTPEndpoint
from starlette.responses import PlainTextResponse, JSONResponse

from controller.transfer.labelstudio import import_preperator
from submodules.model.business_objects.tokenization import is_doc_bin_creation_running
from submodules.s3 import controller as s3
from submodules.model.business_objects import attribute, organization

from controller.transfer import manager as transfer_manager
from controller.upload_task import manager as upload_task_manager
from controller.auth import manager as auth_manager
from controller.transfer import manager as transfer_manager
from controller.transfer import association_transfer_manager
from controller.auth import manager as auth
from controller.project import manager as project_manager
from controller.attribute import manager as attribute_manager

from submodules.model import enums, exceptions
from util.notification import create_notification
from submodules.model.enums import AttributeState, NotificationType
from submodules.model.models import UploadTask
from submodules.model.business_objects import general, tokenization
from util import notification
from controller.tokenization import tokenization_service

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Notify(HTTPEndpoint):
    async def post(self, request) -> PlainTextResponse:
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

        task = upload_task_manager.get_upload_task_secure(
            upload_task_id=upload_task_id,
            project_id=project_id,
            file_name=file_name,
        )
        is_global_update = True if task.file_type == "project" else False
        try:
            init_file_import(task, project_id, is_global_update)
        except Exception:
            file_import_error_handling(task, project_id, is_global_update)
        notification.send_organization_update(
            project_id, f"project_update:{project_id}", True
        )
        return PlainTextResponse("OK")


class FileExport(HTTPEndpoint):
    def get(self, request) -> JSONResponse:
        project_id = request.path_params["project_id"]
        user_id = request.query_params["user_id"]
        num_samples = request.query_params.get("num_samples")
        try:
            auth_manager.check_project_access_from_user_id(
                user_id, project_id, from_api=True
            )
        except exceptions.EntityNotFoundException:
            return JSONResponse({"error": "Could not find project"}, status_code=404)
        except exceptions.AccessDeniedException:
            return JSONResponse({"error": "Access denied"}, status_code=403)
        result = transfer_manager.export_records(project_id, num_samples)
        return JSONResponse(result)


class KnowledgeBaseExport(HTTPEndpoint):
    def get(self, request) -> JSONResponse:
        project_id = request.path_params["project_id"]
        list_id = request.path_params["knowledge_base_id"]
        user_id = request.query_params["user_id"]
        try:
            auth_manager.check_project_access_from_user_id(
                user_id, project_id, from_api=True
            )
        except exceptions.EntityNotFoundException:
            return JSONResponse({"error": "Could not find project"}, status_code=404)
        except exceptions.AccessDeniedException:
            return JSONResponse({"error": "Access denied"}, status_code=403)
        result = transfer_manager.export_knowledge_base(project_id, list_id)
        return JSONResponse(result)


class PrepareFileImport(HTTPEndpoint):
    async def post(self, request) -> JSONResponse:
        auth.check_is_demo_without_info()
        project_id = request.path_params["project_id"]
        request_body = await request.json()

        user_id = request_body["user_id"]
        try:
            auth_manager.check_project_access_from_user_id(
                user_id, project_id, from_api=True
            )
        except exceptions.EntityNotFoundException:
            return JSONResponse({"error": "Could not find project"}, status_code=404)
        except exceptions.AccessDeniedException:
            return JSONResponse({"error": "Access denied"}, status_code=403)
        file_name = request_body["file_name"]
        file_type = request_body["file_type"]
        file_import_options = request_body.get("file_import_options")
        task = upload_task_manager.create_upload_task(
            user_id,
            project_id,
            file_name,
            file_type,
            file_import_options,
            upload_type=enums.UploadTypes.DEFAULT.value,
        )
        org_id = organization.get_id_by_project_id(project_id)
        credentials_and_id = s3.get_upload_credentials_and_id(
            org_id, f"{project_id}/{task.id}"
        )
        return JSONResponse(credentials_and_id)


class JSONImport(HTTPEndpoint):
    async def post(self, request) -> JSONResponse:
        auth.check_is_demo_without_info()
        project_id = request.path_params["project_id"]
        request_body = await request.json()
        user_id = request_body["user_id"]
        auth_manager.check_project_access_from_user_id(user_id, project_id)

        records = request_body["records"]

        project = project_manager.get_project(project_id)
        num_project_records = len(project.records)
        for attribute in project.attributes:
            if attribute.is_primary_key:
                for idx, record in enumerate(records):
                    if attribute.name not in record:
                        if attribute.name == "running_id":
                            records[idx][attribute.name] = num_project_records + idx + 1
                        else:
                            raise exceptions.InvalidInputException(
                                f"Non-running-id, primary key {attribute.name} missing in record"
                            )

        transfer_manager.import_records_from_json(
            project_id,
            user_id,
            records,
            request_body["request_uuid"],
            request_body["is_last"],
        )
        return JSONResponse({"success": True})


class AssociationsImport(HTTPEndpoint):
    async def post(self, request) -> JSONResponse:
        project_id = request.path_params["project_id"]
        request_body = await request.json()
        user_id = request_body["user_id"]
        try:
            auth_manager.check_project_access_from_user_id(
                user_id, project_id, from_api=True
            )
        except exceptions.EntityNotFoundException:
            return JSONResponse({"error": "Could not find project"}, status_code=404)
        except exceptions.AccessDeniedException:
            return JSONResponse({"error": "Access denied"}, status_code=403)
        new_associations_added = association_transfer_manager.import_associations(
            project_id,
            user_id,
            request_body["name"],
            request_body["label_task_name"],
            request_body["associations"],
            request_body["indices"],
            request_body["source_type"],
        )
        return JSONResponse(new_associations_added)


class UploadTask(HTTPEndpoint):
    def get(self, request) -> JSONResponse:
        auth.check_is_demo_without_info()
        project_id = request.path_params["project_id"]
        task_id = request.path_params["task_id"]
        user_id = request.query_params["user_id"]
        try:
            auth_manager.check_project_access_from_user_id(
                user_id, project_id, from_api=True
            )
        except exceptions.EntityNotFoundException:
            return JSONResponse({"error": "Could not find project"}, status_code=404)
        except exceptions.AccessDeniedException:
            return JSONResponse({"error": "Access denied"}, status_code=403)
        task = upload_task_manager.get_upload_task(project_id, task_id)
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
    task_state = task.state
    if "records" in task.file_type:
        if task.upload_type == enums.UploadTypes.LABEL_STUDIO.value:
            import_preperator.prepare_label_studio_import(project_id, task)
        else:
            transfer_manager.import_records_from_file(project_id, task)
        calculate_missing_attributes(project_id, task.user_id)
    elif "project" in task.file_type:
        transfer_manager.import_project(project_id, task)
    elif "knowledge_base" in task.file_type:
        transfer_manager.import_knowledge_base(project_id, task)

    if task.state == task_state:
        # update is sent in update task if it was updated (e.g. with labeling studio)
        notification.send_organization_update(
            project_id,
            f"file_upload:{str(task.id)}:state:{task.state}",
            is_global_update,
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
        upload_task_manager.get_upload_task_message(
            task,
        )
    )
    print(traceback.format_exc(), flush=True)
    notification.send_organization_update(
        project_id, f"file_upload:{str(task.id)}:state:{task.state}", is_global_update
    )


def calculate_missing_attributes(project_id: str, user_id: str) -> None:
    attributes_usable = attribute.get_all(
        project_id,
        state_filter=[
            enums.AttributeState.USABLE.value,
        ],
    )
    if len(attributes_usable) == 0:
        return

    if not check_if_tokenization_finished(project_id):
        for att_usable in attributes_usable:
            attribute.update(
                project_id,
                att_usable.id,
                state=enums.AttributeState.RUNNING.value,
            )

    print("check if tokenization finished", check_if_tokenization_finished(project_id))
    if check_if_tokenization_finished(project_id):
        for att_usable in attributes_usable:
            attribute_manager.calculate_user_attribute_all_records(
                project_id,
                user_id,
                att_usable.id,
            )
            check_if_running = attribute.get_all(
                project_id=project_id, state_filter=[enums.AttributeState.RUNNING.value]
            )
            while check_if_running and not check_if_tokenization_finished(project_id):
                time.sleep(10)
        else:
            time.sleep(10)


def check_if_tokenization_finished(project_id):
    tokenization_task = tokenization.get_record_tokenization_task(project_id)
    return tokenization_task.progress == 1 and (
        project_manager.is_rats_tokenization_still_running(project_id) == False
    )
