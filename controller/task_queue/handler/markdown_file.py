from typing import Any, Dict, Tuple, Callable
from submodules.model.business_objects import (
    task_queue as task_queue_db_bo,
    general,
)
from submodules.model.cognition_objects import (
    markdown_file as markdown_file_db_bo,
)


def get_task_functions() -> Tuple[Callable, Callable, int]:
    return __start_task, __check_finished, 1


def __start_task(task: Dict[str, Any]) -> bool:
    # check task still relevant
    task_db_obj = task_queue_db_bo.get(task["id"])
    if task_db_obj is None or task_db_obj.is_active:
        return False
    return True


def __check_finished(task: Dict[str, Any]) -> bool:
    project_id = task["project_id"]
