from fastapi import APIRouter, Request
from typing import Dict
from controller.task_queue import manager
from fast_api.routes.client_response import pack_json_result


router = APIRouter()


@router.get("/{project_id}/queued-tasks/{task_type}")
def get_project_by_project_id(
    request: Request, project_id: str, task_type: str
) -> Dict:
    data = manager.get_all_waiting_by_type(project_id, task_type)
    return pack_json_result({"data": {"queuedTasks": data}})
