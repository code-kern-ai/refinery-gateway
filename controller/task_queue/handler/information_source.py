from typing import Any, Dict, Tuple, Callable
from controller.payload import manager as payload_manager
from controller.zero_shot import manager as zero_shot_manager
from submodules.model.business_objects import (
    task_queue as task_queue_db_bo,
    general,
    information_source as information_source_db_bo,
)
from submodules.model.enums import PayloadState, InformationSourceType
from ..util import if_task_queue_send_websocket

TASK_DONE_STATES = [PayloadState.FINISHED.value, PayloadState.FAILED.value]


def get_task_functions() -> Tuple[Callable, Callable, int]:
    return __start_task, __check_finished, 1


def __start_task(task: Dict[str, Any]) -> bool:
    # check task still relevant
    task_db_obj = task_queue_db_bo.get(task["id"])
    if task_db_obj is None or task_db_obj.is_active:
        return False
    project_id = task["project_id"]
    information_source_id = task["task_info"]["information_source_id"]
    # check information source still exists

    is_item = information_source_db_bo.get(project_id, information_source_id)
    if is_item is None:
        return False
    task_db_obj.is_active = True
    general.commit()
    user_id = task["created_by"]
    payload_id = None
    if is_item.type == InformationSourceType.ZERO_SHOT.value:
        payload_id = zero_shot_manager.start_zero_shot_for_project_thread(
            project_id, information_source_id, user_id
        )
    else:
        payload = payload_manager.create_payload(
            project_id, information_source_id, user_id
        )
        payload_id = str(payload.id)
    task["task_info"]["payload_id"] = payload_id
    if_task_queue_send_websocket(
        task["task_info"],
        f"INFORMATION_SOURCE:{information_source_id}:{payload_id}:{is_item.name}",
    )
    return True


def __check_finished(task: Dict[str, Any]) -> bool:
    project_id = task["project_id"]
    information_source_id = task["task_info"]["information_source_id"]
    is_item = information_source_db_bo.get(project_id, information_source_id)
    if is_item is None:
        return True
    payload_id = task["task_info"]["payload_id"]
    payload_item = information_source_db_bo.get_payload(project_id, payload_id)
    if payload_item is None:
        return True
    return payload_item.state in TASK_DONE_STATES
