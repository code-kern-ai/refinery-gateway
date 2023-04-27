from typing import Any, List, Dict, Tuple, Callable

from submodules.model import enums, Record


import os
from submodules.model.business_objects import task_queue as task_queue_db_bo
from submodules.model.models import TaskQueue as TaskQueueDBObj
from .handler import embedding as embedding_handler
import copy

from controller.task_queue import task_queue


def add_task(
    project_id: str,
    type: enums.TaskType,
    user_id: str,
    task_info: Dict[str, str],
    priority: bool = False,
):
    task_obj = task_queue_db_bo.add_task_to_queue(
        project_id, type, user_id, task_info, priority, with_commit=True
    )

    add_task_to_task_queue(task_obj)


def get_all_waiting_by_type(project_id: str, type: str) -> List[TaskQueueDBObj]:
    try:
        type_parsed = enums.TaskType[type.upper()]
    except KeyError:
        raise ValueError(f"Invalid Task Type: {type}")

    return task_queue_db_bo.get_all_waiting_by_type(project_id, type_parsed)


def parse_task_to_dict(task: TaskQueueDBObj) -> Dict[str, Any]:
    # copy to unlink from db environment
    return {
        "id": str(task.id),
        "project_id": str(task.project_id),
        "type": str(task.type),
        "created_by": str(task.created_by),
        "priority": bool(task.priority),
        "is_active": bool(task.is_active),
        "task_info": copy.deepcopy(task.task_info),
    }


def get_task_function_by_type(type: str) -> Tuple[Callable, Callable, int]:
    if type == enums.TaskType.EMBEDDING.value:
        return embedding_handler.get_task_functions()
    raise ValueError(f"Task type {type} not supported yet")


def add_task_to_task_queue(task: TaskQueueDBObj):
    start_func, check_func, check_every = get_task_function_by_type(task.type)
    task_queue.get_task_queue().add_task(task, start_func, check_func, check_every)


def remove_task_from_queue(project_id: str, task_id: str):
    task_queue_db_bo.remove_task_from_queue(project_id, task_id, with_commit=True)
    # no need to dequeue from tasks since the initial check should handle it
