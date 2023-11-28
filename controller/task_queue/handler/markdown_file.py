from typing import Any, Dict, Tuple, Callable

import requests
from submodules.model.business_objects import (
    task_queue as task_queue_db_bo,
    general,
)
from submodules.model.cognition_objects import (
    markdown_file as markdown_file_db_bo,
)
from submodules.model import enums


def get_task_functions() -> Tuple[Callable, Callable, int]:
    return __start_task, __check_finished, 1


def __start_task(task: Dict[str, Any]) -> bool:
    # check task still relevant
    task_db_obj = task_queue_db_bo.get(task["id"])
    if task_db_obj is None or task_db_obj.is_active:
        return False
    
    print("Starting markdown file task", flush=True)
    action = task["task_info"]
    dataset_id = action["dataset_id"]
    file_id = action["file_id"]

    task_db_obj.is_active = True
    general.commit()
    requests.post(f"http://cognition-gateway:80/converters-noop/datasets/{dataset_id}/files/{file_id}/parse")
    return True


def __check_finished(task: Dict[str, Any]) -> bool:
    action = task["task_info"]
    file_id = action["file_id"]
    markdown_file_entity = markdown_file_db_bo.get(file_id)

    if markdown_file_entity.state == enums.CognitionMarkdownFileState.FINISHED.value or markdown_file_entity.state == enums.CognitionMarkdownFileState.FAILED.value:
        print("Markdown file finished", flush=True)
        return True
    else:
        return False
