from typing import Any, Dict, Tuple, Callable
import os
import submodules.s3.controller as s3

import requests
from submodules.model.business_objects import (
    task_queue as task_queue_db_bo,
    general,
)

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
    conversation_id = action["conversation_id"]
    cognition_project_id = action["cognition_project_id"]
    requests.post(
        f"{BASE_URI}/api/v1/converters/internal/projects/{cognition_project_id}/conversation/{conversation_id}/parse-tmp-file",
        json={"minio_path": action["minio_path"], "bucket": action["bucket"]},
    )
    return True


def __check_finished(task: Dict[str, Any]) -> bool:

    action = task["task_info"]

    return not s3.object_exists(action["bucket"], action["minio_path"])
