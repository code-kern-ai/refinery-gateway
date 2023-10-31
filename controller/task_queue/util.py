from util import notification

from typing import Any, Dict


def if_task_queue_send_websocket(
    task: Dict[str, Any], msg: str, info_type: str = "START"
) -> None:
    task_queue_id = task.get("parent_task_queue_id")
    if not task_queue_id:
        return

    project_id = task["project_id"]
    notification.send_organization_update(
        project_id, f"task_queue:{task_queue_id}:{info_type}:{msg}"
    )
