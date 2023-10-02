from typing import Any, Dict, Tuple, Callable
from submodules.model.business_objects import (
    task_queue as task_queue_db_bo,
    general,
    attribute as attribute_db_bo,
)
from controller.tokenization import tokenization_service
from submodules.model.business_objects.tokenization import is_doc_bin_creation_running
from submodules.model.enums import RecordTokenizationScope
from ..util import if_task_queue_send_websocket


def get_task_functions() -> Tuple[Callable, Callable, int]:
    return __start_task, __check_finished, 2


def __start_task(task: Dict[str, Any]) -> bool:
    # check task still relevant
    task_db_obj = task_queue_db_bo.get(task["id"])
    if task_db_obj is None or task_db_obj.is_active:
        return False
    project_id = task["project_id"]

    if task["task_info"]["scope"] == RecordTokenizationScope.ATTRIBUTE.value:
        attribute_item = attribute_db_bo.get(
            project_id, task["task_info"]["attribute_id"]
        )
        if attribute_item is None:
            task_queue_db_bo.remove_task_from_queue(project_id, task["id"], True)
            return False
    task_db_obj.is_active = True
    general.commit()
    if_task_queue_send_websocket(task["task_info"], f"TOKENIZATION")

    if task["task_info"]["scope"] == RecordTokenizationScope.PROJECT.value:
        tokenization_service.request_tokenize_project(
            project_id,
            task["created_by"],
            task["task_info"]["include_rats"],
            task["task_info"]["only_uploaded_attributes"],
        )
    else:
        tokenization_service.request_tokenize_calculated_attribute(
            project_id,
            task["created_by"],
            task["task_info"]["attribute_id"],
            task["task_info"]["include_rats"],
        )

    return True


def __check_finished(task: Dict[str, Any]) -> bool:
    return not is_doc_bin_creation_running(task["project_id"])
