from typing import Any, Dict, Tuple, Callable
from controller.payload import manager as payload_manager
from controller.zero_shot import manager as zero_shot_manager
from submodules.model.business_objects import (
    task_queue as task_queue_db_bo,
    general,
    information_source as information_source_db_bo,
)
from submodules.model.enums import TaskType

from .. import manager


def get_task_functions() -> Tuple[Callable, Callable, int]:
    return __start_task, __check_finished, 1


# task queues work a bit different from others since they are just wrapper around tasks in order
def __start_task(task: Dict[str, Any]) -> bool:
    # check task still relevant
    task_db_obj = task_queue_db_bo.get(task["id"])
    if task_db_obj is None or task_db_obj.is_active:
        return False
    if len(task["task_info"]) == 0:
        return False
    if not isinstance(task["task_info"], list):
        raise ValueError("Something is wrong")

    return True


def __check_finished(task: Dict[str, Any]) -> bool:
    sub_task_id = task.get("sub_task_id")
    if not sub_task_id:
        # no sub task yet
        __start_sub_task(task)
        return False
    sub_task_item = task_queue_db_bo.get(sub_task_id)
    if sub_task_item:
        # current sub task still running
        return False

    if len(task["task_info"]) > 0:
        # still further sub task items
        __start_sub_task(task)
        return False
    return True


def __start_sub_task(task: Dict[str, Any]) -> str:
    project_id = task["project_id"]
    user_id = task["created_by"]

    next_entry = task["task_info"].pop(0)
    task_type = next_entry.get("task_type")
    del next_entry["task_type"]

    try:
        task_type_parsed = TaskType[task_type.upper()]
    except KeyError:
        raise ValueError(f"Invalid Task Type: {task_type}")
    task_id = manager.add_task(project_id, task_type_parsed, user_id, next_entry, False)

    task["sub_task_id"] = task_id
    task_queue_db_bo.update_task_info(task["id"], task["task_info"], True)
