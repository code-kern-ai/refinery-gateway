from typing import Any, Dict, Tuple, Callable
from submodules.model.business_objects import (
    task_queue as task_queue_db_bo,
    general,
)
from controller.tokenization import tokenization_service
from submodules.model.business_objects.tokenization import is_doc_bin_creation_running


def get_task_functions() -> Tuple[Callable, Callable, int]:
    return __start_task, __check_finished, 2


def __start_task(task: Dict[str, Any]) -> bool:

    # check task still relevant
    task_db_obj = task_queue_db_bo.get(task["id"])
    if task_db_obj is None or task_db_obj.is_active:
        return False
    project_id = task["project_id"]

    task_db_obj.is_active = True
    general.commit()

    if task["task_info"]["type"] == "project":
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
