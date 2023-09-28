from typing import Any, Dict, Tuple, Callable
from controller.attribute import manager as attribute_manager
from submodules.model.business_objects import (
    task_queue as task_queue_db_bo,
    general,
    attribute as attribute_db_bo,
)
from submodules.model.enums import AttributeState, DataTypes


def get_task_functions() -> Tuple[Callable, Callable, int]:
    return __start_task, __check_finished, 1


def __start_task(task: Dict[str, Any]) -> bool:
    # check task still relevant
    task_db_obj = task_queue_db_bo.get(task["id"])
    if task_db_obj is None or task_db_obj.is_active:
        return False
    project_id = task["project_id"]
    attribute_id = task["task_info"]["attribute_id"]
    # check attribute still exists

    attribute_item = attribute_db_bo.get(project_id, attribute_id)
    if attribute_item is None:
        return False
    task_db_obj.is_active = True
    general.commit()

    attribute_manager.calculate_user_attribute_all_records(
        project_id, task["created_by"], attribute_id
    )
    return True


def __check_finished(task: Dict[str, Any]) -> bool:
    project_id = task["project_id"]
    attribute_id = task["task_info"]["attribute_id"]
    attribute_item = attribute_db_bo.get(project_id, attribute_id)
    if attribute_item is None:
        return True
    if attribute_item.state == AttributeState.FAILED.value:
        return True
    if attribute_item.state == AttributeState.USABLE.value:
        if attribute_item.data_type != DataTypes.EMBEDDING_LIST.value:
            return attribute_db_bo.is_attribute_tokenization_finished(
                project_id, attribute_id
            )
        return True
