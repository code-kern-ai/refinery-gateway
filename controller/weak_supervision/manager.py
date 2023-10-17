from typing import Optional

from submodules.model import enums, WeakSupervisionTask
from submodules.model.business_objects import weak_supervision
import traceback
from typing import Optional, Dict
from controller.embedding import manager as embedding_manager
from submodules.model import enums
from submodules.model.business_objects import (
    labeling_task,
    general,
    record_label_association,
    weak_supervision,
)
from submodules.model.business_objects.information_source import (
    get_selected_information_sources,
)
from submodules.model.business_objects.labeling_task import (
    get_selected_labeling_task_names,
)
from submodules.model.enums import NotificationType
from util import daemon, notification
from controller.weak_supervision.weak_supervision_service import (
    initiate_weak_supervision,
)
from util.notification import create_notification


def run_weak_supervision(
        project_id: str,
        user_id:str,
        overwrite_default_precision: Optional[float] = None,
        overwrite_weak_supervision: Optional[Dict[str, float]] = None,):
    create_notification(
        NotificationType.WEAK_SUPERVISION_TASK_STARTED,
        user_id,
        project_id,
        "Weak Supervision Task",
    )
    notification.send_organization_update(project_id, "weak_supervision_started")

    weak_supervision_task = create_task(
        project_id=project_id,
        created_by=user_id,
        selected_information_sources=get_selected_information_sources(project_id),
        selected_labeling_tasks=get_selected_labeling_task_names(project_id),
    )
    record_label_association.update_used_information_sources(
        project_id, str(weak_supervision_task.id), with_commit=True
    )

    def execution_pipeline(
        project_id: str,
        user_id: str,
        weak_supervision_task_id: str,
        overwrite_default_precision: Optional[float] = None,
        overwrite_weak_supervision: Optional[Dict[str, float]] = None,
    ):
        ctx_token = general.get_ctx_token()
        try:
            labeling_tasks = labeling_task.get_labeling_tasks_by_selected_sources(
                project_id
            )
            for labeling_task_item in labeling_tasks:
                overwrite_ws = overwrite_default_precision
                if overwrite_weak_supervision is not None:
                    overwrite_ws = overwrite_weak_supervision.get(
                        str(labeling_task_item.id)
                    )
                initiate_weak_supervision(
                    project_id,
                    labeling_task_item.id,
                    user_id,
                    weak_supervision_task_id,
                    overwrite_ws,
                )
            update_weak_supervision_task_stats(
                weak_supervision_task_id, project_id
            )
            embedding_manager.update_label_payloads_for_neural_search(project_id)
            create_notification(
                NotificationType.WEAK_SUPERVISION_TASK_DONE,
                user_id,
                project_id,
                "Weak Supervision Task",
            )
            notification.send_organization_update(
                project_id, "weak_supervision_finished"
            )
        except Exception as e:
            print(traceback.format_exc(), flush=True)
            general.rollback()
            weak_supervision.update_state(
                project_id,
                weak_supervision_task_id,
                enums.PayloadState.FAILED.value,
                with_commit=True,
            )
            notification.send_organization_update(
                project_id, "weak_supervision_finished"
            )
            raise e
        finally:
            general.reset_ctx_token(ctx_token)

    daemon.run(
        execution_pipeline,
        project_id,
        str(user_id),
        str(weak_supervision_task.id),
        overwrite_default_precision,
        overwrite_weak_supervision,
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
