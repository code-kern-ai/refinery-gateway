import logging

import graphene
import traceback

from controller.auth import manager as auth
from controller.weak_supervision import manager as ws_manager
from controller.payload import manager as pl_manager
from submodules.model import events, enums
from submodules.model.business_objects import (
    project,
    labeling_task,
    general,
    record_label_association,
    weak_supervision,
)
from submodules.model.business_objects.information_source import (
    get_selected_information_sources,
    get_task_information_sources,
)
from submodules.model.business_objects.labeling_task import (
    get,
    get_selected_labeling_task_names,
)
from submodules.model.enums import NotificationType
from util import daemon, doc_ock
from util import notification
from controller.weak_supervision.weak_supervision_service import (
    initiate_weak_supervision,
)
from util.notification import create_notification

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class InitiateWeakSupervisionByProjectId(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str):
        auth.check_is_demo(info)
        auth.check_project_access(info, project_id)
        user = auth.get_user_by_info(info)
        create_notification(
            NotificationType.WEAK_SUPERVISION_TASK_STARTED,
            user.id,
            project_id,
            "Weak Supervision Task",
        )
        notification.send_organization_update(project_id, f"weak_supervision_started")

        weak_supervision_task = ws_manager.create_task(
            project_id=project_id,
            created_by=user.id,
            selected_information_sources=get_selected_information_sources(project_id),
            selected_labeling_tasks=get_selected_labeling_task_names(project_id),
        )
        record_label_association.update_used_information_sources(
            project_id, str(weak_supervision_task.id), with_commit=True
        )

        def execution_pipeline(
            project_id: str, user_id: str, weak_supervision_task_id: str
        ):
            ctx_token = general.get_ctx_token()
            try:
                labeling_tasks = labeling_task.get_labeling_tasks_by_selected_sources(
                    project_id
                )
                for labeling_task_item in labeling_tasks:
                    initiate_weak_supervision(
                        project_id,
                        labeling_task_item.id,
                        user_id,
                        weak_supervision_task_id,
                    )
                ws_manager.update_weak_supervision_task_stats(
                    weak_supervision_task_id, project_id
                )
                create_notification(
                    NotificationType.WEAK_SUPERVISION_TASK_DONE,
                    user_id,
                    project_id,
                    "Weak Supervision Task",
                )
                notification.send_organization_update(
                    project_id, f"weak_supervision_finished"
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
                    project_id, f"weak_supervision_finished"
                )
                raise e
            finally:
                general.reset_ctx_token(ctx_token, True)

        daemon.run(
            execution_pipeline, project_id, str(user.id), str(weak_supervision_task.id)
        )
        return InitiateWeakSupervisionByProjectId(ok=True)


class RunInformationSourceAndInitiateWeakSupervisionByLabelingTaskId(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        information_source_id = graphene.ID(required=True)
        labeling_task_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(
        self, info, project_id: str, information_source_id: str, labeling_task_id: str
    ):
        auth.check_is_demo(info)
        auth.check_project_access(info, project_id)
        user = auth.get_user_by_info(info)
        pl_manager.create_payload(
            info, project_id, information_source_id, user.id, asynchronous=False
        )
        labeling_task_item = labeling_task.get(project_id, labeling_task_id)
        for information_source in labeling_task_item.information_sources:
            information_source.is_selected = any(
                source_statistic.true_positives > 0
                for source_statistic in information_source.source_statistics
                if source_statistic.true_positives is not None
            )
        general.commit()

        source_names = get_task_information_sources(project_id, labeling_task_id)
        if len(source_names) > 0:
            create_notification(
                NotificationType.WEAK_SUPERVISION_TASK_STARTED,
                user.id,
                project_id,
                "Weak Supervision Task",
            )
            notification.send_organization_update(
                project_id, f"weak_supervision_started"
            )

            weak_supervision_task = ws_manager.create_task(
                project_id=project_id,
                created_by=user.id,
                selected_information_sources=source_names,
                selected_labeling_tasks=labeling_task_item.name,
            )
            record_label_association.update_used_information_sources(
                project_id, str(weak_supervision_task.id), with_commit=True
            )
            try:
                initiate_weak_supervision(
                    project_id,
                    labeling_task_id,
                    user.id,
                    weak_supervision_task.id,
                )
                ws_manager.update_weak_supervision_task_stats(
                    weak_supervision_task.id, project_id
                )
                create_notification(
                    NotificationType.WEAK_SUPERVISION_TASK_DONE,
                    user.id,
                    project_id,
                    "Weak Supervision Task",
                )
                notification.send_organization_update(
                    project_id, f"weak_supervision_finished"
                )
            except Exception as e:
                print(traceback.format_exc(), flush=True)
                general.rollback()
                weak_supervision.update_state(
                    project_id,
                    weak_supervision_task.id,
                    enums.PayloadState.FAILED.value,
                    with_commit=True,
                )
                notification.send_organization_update(
                    project_id, f"weak_supervision_finished"
                )
                raise e
        else:
            create_notification(
                NotificationType.WEAK_SUPERVISION_TASK_FAILED,
                user.id,
                project_id,
                "Weak Supervision Task",
            )
            notification.send_organization_update(
                project_id, f"weak_supervision_failed"
            )
        return RunInformationSourceAndInitiateWeakSupervisionByLabelingTaskId(ok=True)


class WeakSupervisionMutation(graphene.ObjectType):
    initiate_weak_supervision_by_project_id = InitiateWeakSupervisionByProjectId.Field()
    run_heuristic_then_trigger_weak_supervision = (
        RunInformationSourceAndInitiateWeakSupervisionByLabelingTaskId.Field()
    )
