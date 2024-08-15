from typing import Any, List, Dict
import copy
from submodules.model import enums
from submodules.model.business_objects import (
    task_queue as task_queue_db_bo,
)
from submodules.model.models import TaskQueue as TaskQueueDBObj


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


def remove_task_from_queue(project_id: str, task_id: str) -> None:
    task_queue_db_bo.remove_task_from_queue(project_id, task_id, with_commit=True)
    # no need to dequeue from tasks since the initial check should handle it
