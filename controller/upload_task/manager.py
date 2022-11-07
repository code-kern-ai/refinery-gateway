import logging
from typing import Optional

from controller.transfer.util import (
    get_upload_task_message as get_upload_task_message_orig,
)
from submodules.model import UploadTask, enums
from submodules.model.business_objects import upload_task, general
from util import notification

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_upload_task(project_id: str, task_id: str) -> UploadTask:
    return upload_task.get(project_id, task_id)


def get_upload_task_secure(
    project_id: str,
    upload_task_id: str,
    file_name: str,
) -> UploadTask:
    return upload_task.get_with_file_name(project_id, upload_task_id, file_name)


def get_upload_task_message(
    task: UploadTask,
    include_duration: Optional[bool] = True,
    additional_information: str = "",
) -> str:
    return get_upload_task_message_orig(task, include_duration, additional_information)


def create_upload_task(
    user_id: str,
    project_id: str,
    file_name: str,
    file_type: str,
    file_import_options: str,
    upload_type: str,
) -> UploadTask:
    task = upload_task.create(
        user_id,
        project_id,
        file_name,
        file_type,
        file_import_options,
        upload_type,
        with_commit=True,
    )
    return task


def update_upload_task_to_finished(task: UploadTask) -> None:
    upload_task.finish(task.project_id, task.id, with_commit=True)


def update_task(
    project_id: str,
    task_id: str,
    state: Optional[str] = None,
    progress: Optional[float] = None,
) -> None:

    if progress is not None:
        if progress < 0 or progress > 100:
            raise Exception(f"Progress out of bounds. Progress is {progress}")

    upload_task.update(project_id, task_id, state=state, progress=progress, with_commit=True)
    if state:
        notification.send_organization_update(
            project_id, f"file_upload:{str(task_id)}:state:{state}"
        )

    notification.send_organization_update(
        project_id, f"file_upload:{str(task_id)}:progress:{progress}"
    )
    task = get_upload_task(project_id, task_id)
    logger.info(get_upload_task_message(task))

    do_notify = False
    notification_type = None
    if state == enums.UploadStates.PENDING.value:
        do_notify = True
        notification_type = enums.NotificationType.IMPORT_STARTED.value
    elif state == enums.UploadStates.DONE.value:
        do_notify = True
        notification_type = enums.NotificationType.IMPORT_DONE.value
    if do_notify:
        notification.create_notification(
            notification_type,
            task.user_id,
            project_id,
            "Record",
        )
