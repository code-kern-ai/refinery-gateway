from typing import Any, Dict, Tuple, Callable
from controller.embedding import manager as embedding_manager
from submodules.model import enums
from submodules.model.business_objects import (
    agreement as agreement_db_bo,
    attribute as attribute_db_bo,
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
    embedding_type = task["task_info"]["embedding_type"]
    embedding_name = task["task_info"]["embedding_name"]
    platform = task["task_info"]["platform"]
    model = task["task_info"]["model"]
    api_token = task["task_info"]["api_token"]

    terms_text = task["task_info"]["terms_text"]
    terms_accepted = task["task_info"]["terms_accepted"]

    filter_attributes = task["task_info"]["filter_attributes"]
    additional_data = task["task_info"]["additional_data"]
    embedding_item = embedding_db_bo.create(
        project_id,
        attribute_id,
        embedding_name,
        user_id,
        enums.EmbeddingState.INITIALIZING.value,
        type=embedding_type,
        model=model,
        platform=platform,
        api_token=api_token,
        filter_attributes=filter_attributes,
        additional_data=additional_data,
    )
    if (
        platform == enums.EmbeddingPlatform.OPENAI.value
        or platform == enums.EmbeddingPlatform.COHERE.value
    ):
        agreement_db_bo.create(
            project_id,
            user_id,
            terms_text,
            terms_accepted,
            xfkey=embedding_item.id,
            xftype=enums.AgreementType.EMBEDDING.value,
        )

    general.commit()

    embedding_manager.create_embedding(project_id, str(embedding_item.id))

    return True


def __check_finished(task: Dict[str, Any]) -> bool:
    embedding_item = embedding_db_bo.get_embedding_by_name(
        task["project_id"], task["task_info"]["embedding_name"]
    )
    # if it doesn't exists anymore, it means it was deleted -> we are done with the task
    if embedding_item is None:
        return True
    return embedding_item.state in TASK_DONE_STATES
