import requests
import os
from submodules.model import enums
from typing import Any, Dict

TASK_MASTER_URL = os.getenv("TASK_MASTER")


def queue_task(
    org_id: str,
    user_id: str,
    task_type: enums.TaskType,
    task_info: Dict[str, Any],
    priority: bool = False,
) -> requests.Response:

    task_payload = {
        "orgId": org_id,
        "userId": user_id,
        "taskType": task_type.value,
        "taskInfo": task_info,
        "priority": priority,
    }
    return requests.put(f"{TASK_MASTER_URL}/task/queue", json=task_payload)
