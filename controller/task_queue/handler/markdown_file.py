from typing import Any, Dict, Tuple, Callable
import os

import requests
from submodules.model.business_objects import (
    task_queue as task_queue_db_bo,
    general,
)
from submodules.model.cognition_objects import (
    markdown_file as markdown_file_db_bo,
)
from submodules.model.enums import CognitionMarkdownFileState

BASE_URI = os.getenv("COGNITION_GATEWAY")

TASK_DONE_STATES = [
    CognitionMarkdownFileState.FINISHED.value,
    CognitionMarkdownFileState.FAILED.value,
]


def get_task_functions() -> Tuple[Callable, Callable, int]:
    return __start_task, __check_finished, 1


def __start_task(task: Dict[str, Any]) -> bool:
    # check task still relevant
    task_db_obj = task_queue_db_bo.get(task["id"])
    if task_db_obj is None or task_db_obj.is_active:
        return False

    action = task["task_info"]
    org_id = action["org_id"]
    dataset_id = action["dataset_id"]
    file_id = action["file_id"]

    task_db_obj.is_active = True
    general.commit()
    requests.post(
        f"{BASE_URI}/api/v1/converters/internal/datasets/{dataset_id}/files/{file_id}/parse",
        json={"orgId": org_id},
    )
    return True


def __check_finished(task: Dict[str, Any]) -> bool:
    action = task["task_info"]
    org_id = action["org_id"]
    file_id = action["file_id"]
    markdown_file_entity = markdown_file_db_bo.get(org_id=org_id, md_file_id=file_id)
    if markdown_file_entity is None:
        return True
    return markdown_file_entity.state in TASK_DONE_STATES
