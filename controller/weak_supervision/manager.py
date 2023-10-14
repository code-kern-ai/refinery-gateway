from typing import Optional

from submodules.model import enums, WeakSupervisionTask
from submodules.model.business_objects import weak_supervision


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
