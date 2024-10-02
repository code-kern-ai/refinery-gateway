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


def delete_task(org_id: str, task_id: str) -> requests.Response:
    return requests.delete(
        f"{TASK_MASTER_URL}/task/queue",
        json={"orgId": str(org_id), "taskId": str(task_id)},
    )


def pause_task_queue(task_queue_pause: bool) -> requests.Response:
    return requests.post(
        f"{TASK_MASTER_URL}/task/queue/pause?task_queue_pause={task_queue_pause}"
    )


def get_task_queue_pause() -> requests.Response:
    return requests.get(f"{TASK_MASTER_URL}/task/queue/pause")
