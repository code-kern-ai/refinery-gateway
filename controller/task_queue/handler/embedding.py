from typing import Any, Dict, Tuple, Callable
from controller.embedding import manager as embedding_manager
from submodules.model.business_objects import (
    task_queue as task_queue_db_bo,
    embedding as embedding_db_bo,
    general,
)
from submodules.model.enums import EmbeddingState, EmbeddingType

TASK_DONE_STATES = [EmbeddingState.FINISHED.value, EmbeddingState.FAILED.value]


def get_task_functions() -> Tuple[Callable, Callable, int]:
    return __start_task, __check_finished, 5


def __start_task(task: Dict[str, Any]) -> bool:

    # check task still relevant
    task_db_obj = task_queue_db_bo.get(task["id"])
    if task_db_obj is None or task_db_obj.is_active:
        return False
    project_id = task["project_id"]

    # check embedding already exists
    embedding_item = embedding_db_bo.get_embedding_id_and_type(
        project_id, task["task_info"]["embedding_name"]
    )
    if embedding_item is not None:
        task_queue_db_bo.remove_task_from_queue(project_id, task["id"], True)
        return False
    task_db_obj.is_active = True
    general.commit()

    user_id = task["created_by"]
    attribute_id = task["task_info"]["attribute_id"]
    embedding_handle = task["task_info"]["embedding_handle"]
    platform = task["task_info"]["platform"]
    if task["task_info"]["embedding_type"] == EmbeddingType.ON_ATTRIBUTE.value:
        embedding_manager.create_attribute_level_embedding(
            project_id, user_id, attribute_id, embedding_handle, platform
        )
    else:
        embedding_manager.create_token_level_embedding(
            project_id, user_id, attribute_id, embedding_handle, platform
        )
    return True


def __check_finished(task: Dict[str, Any]) -> bool:

    embedding_item = embedding_db_bo.get_embedding_by_name(
        task["project_id"], task["task_info"]["embedding_name"]
    )
    # if it doesn't exists anymore, it means it was deleted -> we are done with the task
    if embedding_item is None:
        return True
    return embedding_item.state in TASK_DONE_STATES
