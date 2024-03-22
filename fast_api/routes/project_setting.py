from fastapi import APIRouter, Request
from typing import Dict
from controller.task_queue import manager
from controller.attribute import manager as attribute_manager
from controller.labeling_task_label import manager as label_manager
from fast_api.routes.client_response import pack_json_result
from submodules.model.util import sql_alchemy_to_dict


router = APIRouter()


@router.get("/{project_id}/queued-tasks/{task_type}")
def get_project_by_project_id(
    request: Request, project_id: str, task_type: str
) -> Dict:
    data = manager.get_all_waiting_by_type(project_id, task_type)
    return pack_json_result({"data": {"queuedTasks": data}})


@router.get("/{project_id}/{attribute_id}/attribute-by-id")
def get_attribute_by_attribute_id(project_id: str, attribute_id: str):
    data = sql_alchemy_to_dict(
        attribute_manager.get_attribute(project_id, attribute_id)
    )
    return pack_json_result({"data": {"attributeByAttributeId": data}})


@router.get("/{project_id}/check-rename-label/")
def check_rename_label(project_id: str, label_id: str, new_name: str):
    data = label_manager.check_rename_label(project_id, label_id, new_name)
    return pack_json_result({"data": {"checkRenameLabel": data}})
