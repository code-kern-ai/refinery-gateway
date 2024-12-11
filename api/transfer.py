import logging
import traceback
import time
from typing import Optional
from starlette.endpoints import HTTPEndpoint
from starlette.responses import PlainTextResponse, JSONResponse
from controller.embedding.manager import recreate_embeddings

from controller.transfer.cognition import (
    import_preparator as cognition_preparator,
    import_wizard as cognition_import_wizard,
)
from submodules.model.business_objects import (
    attribute,
    general,
    tokenization,
    project,
)

from submodules.model.cognition_objects import (
    project as cognition_project,
)

from controller.transfer import manager as transfer_manager
from controller.upload_task import manager as upload_task_manager
from controller.auth import manager as auth_manager
from controller.attribute import manager as attribute_manager
from controller.project import manager as project_manager
from submodules.model import enums, exceptions
from util.notification import create_notification
from submodules.model.enums import NotificationType
from submodules.model.models import UploadTask
from util import notification
from submodules.model import daemon

from controller.task_master import manager as task_master_manager
from submodules.model.enums import TaskType, RecordTokenizationScope


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class JSONImport(HTTPEndpoint):
    async def post(self, request) -> JSONResponse:
        project_id = request.path_params["project_id"]
        request_body = await request.json()
        user_id = request_body["user_id"]
        auth_manager.check_project_access_from_user_id(user_id, project_id)

        records = request_body["records"]

        project = project_manager.get_project(project_id)
        num_project_records = len(project.records)
        for att in project.attributes:
            if att.is_primary_key:
                for idx, record in enumerate(records):
                    if att.name not in record:
                        if att.name == "running_id":
                            records[idx][att.name] = num_project_records + idx + 1
                        else:
                            raise exceptions.InvalidInputException(
                                f"Non-running-id, primary key {att.name} missing in record"
                            )

        transfer_manager.import_records_from_json(
            project_id,
            user_id,
            records,
            request_body["request_uuid"],
            request_body["is_last"],
        )
        return JSONResponse({"success": True})


class CognitionImport(HTTPEndpoint):
    def put(self, request) -> PlainTextResponse:
        project_id = request.path_params["project_id"]
        task_id = request.path_params["task_id"]
        task = upload_task_manager.get_upload_task(
            task_id=task_id,
            project_id=project_id,
        )
        if task.upload_type != enums.UploadTypes.COGNITION.value:
            return PlainTextResponse("OK")
        # since upload type is set to COGNITION for the first step of the upload (file upload / mapping prep)
        # this / the continuation of the import should only be done once so we set it back to default to prevent this & differentiate between the steps
        task.upload_type = enums.UploadTypes.DEFAULT.value
        if task.state != enums.UploadStates.PREPARED.value:
            return PlainTextResponse("Bad upload task", status_code=400)
        try:
            init_file_import(task, project_id, False)
        except Exception:
            file_import_error_handling(task, project_id, False)
        notification.send_organization_update(
            project_id, f"project_update:{project_id}", True
        )
        return PlainTextResponse("OK")


class CognitionPrepareProject(HTTPEndpoint):
    def put(self, request) -> PlainTextResponse:
        cognition_project_id = request.path_params["cognition_project_id"]

        cognition_project_item = cognition_project.get(cognition_project_id)
        if not cognition_project_item:
            return PlainTextResponse("Bad project id", status_code=400)
        task_id = request.path_params["task_id"]

        daemon.run_without_db_token(
            cognition_import_wizard.prepare_and_finalize_setup,
            cognition_project_id=cognition_project_id,
            task_id=task_id,
        )

        return PlainTextResponse("OK")


class UploadTaskInfo(HTTPEndpoint):
    def get(self, request) -> JSONResponse:
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
        if task.upload_type == enums.UploadTypes.COGNITION.value:
            cognition_preparator.prepare_cognition_import(project_id, task)
        else:
            transfer_manager.import_records_from_file(project_id, task)
        daemon.run_with_db_token(
            __recalculate_missing_attributes_and_embeddings,
            project_id,
            str(task.user_id),
        )

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
        only_usable_attributes = task.file_type == "records_add"
        project_item = project.get(project_id)
        org_id = project_item.organization_id
        task_master_manager.queue_task(
            str(org_id),
            str(task.user_id),
            TaskType.TOKENIZATION,
            {
                "project_id": str(project_id),
                "scope": RecordTokenizationScope.PROJECT.value,
                "include_rats": True,
                "only_uploaded_attributes": only_usable_attributes,
            },
        )


def file_import_error_handling(
    task: UploadTask,
    project_id: str,
    is_global_update: bool,
    notification_type: Optional[NotificationType] = None,
    print_traceback: bool = True,
) -> None:
    general.rollback()
    task.state = enums.UploadStates.ERROR.value
    general.commit()
    if not notification_type:
        notification_type = NotificationType.IMPORT_FAILED
    create_notification(
        notification_type,
        task.user_id,
        task.project_id,
        task.file_type,
    )
    logger.error(
        upload_task_manager.get_upload_task_message(
            task,
        )
    )
    if print_traceback:
        print(traceback.format_exc(), flush=True)

    notification.send_organization_update(
        project_id, f"file_upload:{str(task.id)}:state:{task.state}", is_global_update
    )


def __recalculate_missing_attributes_and_embeddings(
    project_id: str, user_id: str
) -> None:
    __calculate_missing_attributes(project_id, user_id)
    recreate_embeddings(project_id)


def __calculate_missing_attributes(project_id: str, user_id: str) -> None:
    # wait a second to ensure that the process is started in the tokenization service
    time.sleep(5)
    attributes_usable = attribute.get_all_ordered(
        project_id,
        True,
        state_filter=[
            enums.AttributeState.USABLE.value,
        ],
    )
    if len(attributes_usable) == 0:
        return

    # stored as list so connection results do not affect
    attribute_ids = [str(att_usable.id) for att_usable in attributes_usable]
    for att_id in attribute_ids:
        attribute.update(project_id, att_id, state=enums.AttributeState.INITIAL.value)
    general.commit()
    notification.send_organization_update(
        project_id=project_id, message="calculate_attribute:started:all"
    )
    try:
        # first check project tokenization completed
        i = 0
        while True:
            i += 1
            if i >= 60:
                i = 0
                daemon.reset_session_token_in_thread()
            if tokenization.is_doc_bin_creation_running_or_queued(project_id):
                time.sleep(2)
                continue
            else:
                break
        # next, ensure that the attributes are calculated and tokenized
        i = 0
        while True:
            time.sleep(1)
            i += 1
            if len(attribute_ids) == 0:
                break
            if i >= 60:
                i = 0
                daemon.reset_session_token_in_thread()

            current_att_id = attribute_ids[0]
            current_att = attribute.get(project_id, current_att_id)
            if current_att.state == enums.AttributeState.RUNNING.value:
                continue
            elif current_att.state == enums.AttributeState.INITIAL.value:
                attribute_manager.calculate_user_attribute_all_records(
                    project_id,
                    project.get_org_id(project_id),
                    user_id,
                    current_att_id,
                    True,
                )
            else:
                if tokenization.is_doc_bin_creation_running_for_attribute(
                    project_id, current_att.name
                ):
                    time.sleep(2)
                    continue
                else:
                    attribute_ids.pop(0)
                    notification.send_organization_update(
                        project_id=project_id,
                        message=f"calculate_attribute:finished:{current_att_id}",
                    )
            time.sleep(2)
    except Exception as e:
        print(
            f"Error while recreating attribute calculation for {project_id} when new records are uploaded : {e}"
        )
        get_initial_attributes = attribute.get_all_ordered(
            project_id,
            True,
            state_filter=[
                enums.AttributeState.INITIAL.value,
            ],
        )
        for attr in get_initial_attributes:
            attribute.update(
                project_id, attr.id, state=enums.AttributeState.FAILED.value
            )
        general.commit()
    finally:
        notification.send_organization_update(
            project_id=project_id,
            message="calculate_attribute:finished:all",
        )
