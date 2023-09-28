from typing import Any, Dict, Tuple, Callable
from submodules.model.business_objects import (
    task_queue as task_queue_db_bo,
    project as project_db_bo,
)

from util import notification

from submodules.model.enums import TaskType, InformationSourceType

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
    task["initial_count"] = len(task["task_info"])
    task["done_count"] = 0
    return True


def __check_finished(task: Dict[str, Any]) -> bool:
    project_id = task["project_id"]
    if not project_db_bo.get(project_id):
        # parent project was deleted so the queue item is done
        return True
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
        task["done_count"] += 1
        __send_websocket_progress(task)
        __start_sub_task(task)
        return False

    __send_websocket_progress(task)
    return True


def __start_sub_task(task: Dict[str, Any]) -> str:
    user_id = task["created_by"]

    next_entry = task["task_info"].pop(0)
    task_type = next_entry.get("task_type")
    # if a specific project id is given for the item we use that otherwise the one from the task
    # can e.g. happen with cognition init tasks
    project_id = next_entry.get("project_id", task["project_id"])
    del next_entry["task_type"]

    try:
        task_type_parsed = TaskType[task_type.upper()]
    except KeyError:
        raise ValueError(f"Invalid Task Type: {task_type}")

    priority = False
    if task_type_parsed == TaskType.ATTRIBUTE_CALCULATION:
        priority = True
    elif task_type_parsed == TaskType.INFORMATION_SOURCE:
        priority = (
            next_entry.get("source_type") != InformationSourceType.ZERO_SHOT.value
        )
    elif task_type_parsed == TaskType.TASK_QUEUE_ACTION:
        next_entry = next_entry.get("action")
    task_id = manager.add_task(
        project_id, task_type_parsed, user_id, next_entry, priority
    )

    task["sub_task_id"] = task_id
    task_queue_db_bo.update_task_info(task["id"], task["task_info"], True)


def __send_websocket_progress(task: Dict[str, Any]) -> None:
    project_id = task["project_id"]
    task_id = task["id"]
    if len(task["task_info"]) == 0:
        notification.send_organization_update(
            project_id, f"task_queue:{task_id}:state:DONE"
        )
    else:
        progress = round(task["done_count"] / task["initial_count"], 4)

        notification.send_organization_update(
            project_id, f"task_queue:{task_id}:progress:{progress}"
        )
