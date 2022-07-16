import timeit
from typing import Any, Tuple, Optional

from submodules.model import enums, WeakSupervisionTask
from submodules.model.business_objects import labeling_task
from submodules.model.business_objects import weak_supervision
from controller.weak_supervision.weak_supervision_service import (
    initiate_weak_supervision,
)


def create_task(
    project_id: str,
    created_by: str,
    selected_information_sources: Optional[str] = None,
    selected_labeling_tasks: Optional[str] = None,
) -> WeakSupervisionTask:
    return weak_supervision.create_task(
        project_id=project_id,
        created_by=created_by,
        selected_information_sources=selected_information_sources,
        selected_labeling_tasks=selected_labeling_tasks,
    )


def update_weak_supervision_task_stats(
    weak_supervision_task_id: str, project_id: str
) -> None:
    weak_supervision.update_weak_supervision_task_stats(
        project_id, weak_supervision_task_id
    )
    weak_supervision.update_state(
        project_id,
        weak_supervision_task_id,
        enums.PayloadState.FINISHED.value,
        with_commit=True,
    )


def start_weak_supervision_by_project_id(
    project_id: str, user_id: str, ws_task_id: str
) -> None:
    selected_tasks = labeling_task.get_labeling_tasks_by_selected_sources(project_id)
    for labeling_task_item in selected_tasks:
        initiate_weak_supervision(
            project_id, labeling_task_item.id, user_id, ws_task_id
        )


def start_weak_supervision_by_task_id(
    project_id: str, task_id: str, user_id: str, ws_task_id: str
) -> Tuple[float, float]:
    start = timeit.default_timer()
    initiate_weak_supervision(project_id, task_id, user_id, ws_task_id)
    stop = timeit.default_timer()
    return start, stop
