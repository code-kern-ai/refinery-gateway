from typing import Any, List, Dict, Tuple, Callable

from submodules.model import enums, Record


import os
from submodules.model.business_objects import task_queue as task_queue_db_bo
from submodules.model.models import TaskQueue as TaskQueueDBObj
from .handler import (
    embedding as embedding_handler,
    information_source as information_source_handler,
    tokenization as tokenization_handler,
    attribute_calculation as attribute_calculation_handler,
)
import copy

from controller.task_queue import task_queue


def add_task(
    project_id: str,
    task_type: enums.TaskType,
    user_id: str,
    task_info: Dict[str, str],
    priority: bool = False,
) -> str:
    task_item = task_queue_db_bo.add(
        project_id, task_type, user_id, task_info, priority, with_commit=True
    )
    task_id = str(task_item.id)
    add_task_to_task_queue(task_item)
    return task_id


def get_all_waiting_by_type(project_id: str, task_type: str) -> List[TaskQueueDBObj]:
    try:
        task_type_parsed = enums.TaskType[task_type.upper()]
    except KeyError:
        raise ValueError(f"Invalid Task Type: {task_type}")

    return task_queue_db_bo.get_all_waiting_by_type(project_id, task_type_parsed)


def parse_task_to_dict(task: TaskQueueDBObj) -> Dict[str, Any]:
    # copy to unlink from db environment
    return {
        "id": str(task.id),
        "project_id": str(task.project_id),
        "task_type": str(task.task_type),
        "created_by": str(task.created_by),
        "priority": bool(task.priority),
        "is_active": bool(task.is_active),
        "task_info": copy.deepcopy(task.task_info),
    }


def get_task_function_by_type(task_type: str) -> Tuple[Callable, Callable, int]:
    if task_type == enums.TaskType.EMBEDDING.value:
        return embedding_handler.get_task_functions()
    if task_type == enums.TaskType.INFORMATION_SOURCE.value:
        return information_source_handler.get_task_functions()
    if task_type == enums.TaskType.TOKENIZATION.value:
        return tokenization_handler.get_task_functions()
    if task_type == enums.TaskType.ATTRIBUTE_CALCULATION.value:
        return attribute_calculation_handler.get_task_functions()
    raise ValueError(f"Task type {task_type} not supported yet")


def add_task_to_task_queue(task: TaskQueueDBObj) -> None:
    start_func, check_func, check_every = get_task_function_by_type(task.task_type)
    task_queue.get_task_queue().add_task(task, start_func, check_func, check_every)


def remove_task_from_queue(project_id: str, task_id: str) -> None:
    task_queue_db_bo.remove_task_from_queue(project_id, task_id, with_commit=True)
    # no need to dequeue from tasks since the initial check should handle it
