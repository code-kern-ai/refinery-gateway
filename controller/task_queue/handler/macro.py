from typing import Any, Dict, Tuple, Callable
import os

import requests
from submodules.model.business_objects import (
    task_queue as task_queue_db_bo,
    general,
)

from submodules.model.cognition_objects import macro as macro_db_bo

BASE_URI = os.getenv("COGNITION_GATEWAY")


def get_task_functions() -> Tuple[Callable, Callable, int]:
    return __start_task, __check_finished, 1


def __start_task(task: Dict[str, Any]) -> bool:
    # check task still relevant
    task_db_obj = task_queue_db_bo.get(task["id"])
    if task_db_obj is None or task_db_obj.is_active:
        return False

    task_db_obj.is_active = True
    general.commit()

    action = task["task_info"]

    macro_id = action["macro_id"]
    execution_id = action["execution_id"]
    group_id = action.get("execution_group_id")
    requests.put(
        f"{BASE_URI}/api/v1/converters/internal/macros/{macro_id}/execution/{execution_id}/start?group_execution_id={group_id}"
    )
    return True


def __check_finished(task: Dict[str, Any]) -> bool:

    action = task["task_info"]
    return macro_db_bo.macro_execution_finished(
        action["macro_id"], action["execution_id"], action["execution_group_id"]
    )
