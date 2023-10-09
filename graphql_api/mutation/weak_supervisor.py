import logging

import graphene
import traceback
from typing import Optional, Union, Dict, Any

from controller.auth import manager as auth
from controller.weak_supervision import manager as ws_manager
from controller.payload import manager as pl_manager
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
    get_task_information_sources,
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

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class InitiateWeakSupervisionByProjectId(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        overwrite_default_precision = graphene.Float(required=False)
        overwrite_weak_supervision = graphene.JSONString(required=False)

    ok = graphene.Boolean()

    def mutate(
        self,
        info,
        project_id: str,
        overwrite_default_precision: Optional[float] = None,
        overwrite_weak_supervision: Optional[Dict[str, float]] = None,
    ):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user = auth.get_user_by_info(info)
        create_notification(
            NotificationType.WEAK_SUPERVISION_TASK_STARTED,
            user.id,
            project_id,
            "Weak Supervision Task",
        )
        notification.send_organization_update(project_id, "weak_supervision_started")

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
            project_id: str,
            user_id: str,
            weak_supervision_task_id: str,
            overwrite_weak_supervision: Optional[Union[float, Dict[str, Any]]] = None,
        ):
            ctx_token = general.get_ctx_token()
            try:
                labeling_tasks = labeling_task.get_labeling_tasks_by_selected_sources(
                    project_id
                )
                for labeling_task_item in labeling_tasks:
                    overwrite_ws = None
                    if overwrite_weak_supervision is not None:
                        if isinstance(overwrite_weak_supervision, float):
                            overwrite_ws = overwrite_weak_supervision
                        else:
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
                ws_manager.update_weak_supervision_task_stats(
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
                general.reset_ctx_token(ctx_token, True)

        daemon.run(
            execution_pipeline,
            project_id,
            str(user.id),
            str(weak_supervision_task.id),
            overwrite_weak_supervision or overwrite_default_precision,
        )
        return InitiateWeakSupervisionByProjectId(ok=True)


class RunInformationSourceAndInitiateWeakSupervisionByLabelingTaskId(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        information_source_id = graphene.ID(required=True)
        labeling_task_id = graphene.ID(required=True)
        overwrite_default_precision = graphene.Float(required=False)
        overwrite_weak_supervision = graphene.JSONString(required=False)

    ok = graphene.Boolean()

    def mutate(
        self,
        info,
        project_id: str,
        information_source_id: str,
        labeling_task_id: str,
        overwrite_default_precision: Optional[float] = None,
        overwrite_weak_supervision: Optional[Dict[str, float]] = None,
    ):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user = auth.get_user_by_info(info)
        pl_manager.create_payload(
            project_id, information_source_id, user.id, asynchronous=False
        )
        ws_overwrite = None
        if overwrite_weak_supervision is not None:
            ws_overwrite = overwrite_weak_supervision
        else:
            ws_overwrite = overwrite_default_precision

        source_names = []
        labeling_task_item = labeling_task.get(project_id, labeling_task_id)
        for information_source in labeling_task_item.information_sources:
            information_source.is_selected = (
                information_source.payloads[0].state
                == enums.PayloadState.FINISHED.value
                if len(information_source.payloads) > 0
                else False
            )
            if information_source.is_selected:
                source_names.append(information_source.name)
        general.commit()

        if len(source_names) > 0 or ws_overwrite is not None:
            create_notification(
                NotificationType.WEAK_SUPERVISION_TASK_STARTED,
                user.id,
                project_id,
                "Weak Supervision Task",
            )
            notification.send_organization_update(
                project_id, "weak_supervision_started"
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
                    ws_overwrite,
                )
                ws_manager.update_weak_supervision_task_stats(
                    weak_supervision_task.id, project_id
                )
                embedding_manager.update_label_payloads_for_neural_search(project_id)
                create_notification(
                    NotificationType.WEAK_SUPERVISION_TASK_DONE,
                    user.id,
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
                    weak_supervision_task.id,
                    enums.PayloadState.FAILED.value,
                    with_commit=True,
                )
                notification.send_organization_update(
                    project_id, "weak_supervision_failed"
                )
                raise e
        else:
            create_notification(
                NotificationType.WEAK_SUPERVISION_TASK_NO_VALID_LABELS,
                user.id,
                project_id,
            )
            notification.send_organization_update(project_id, "weak_supervision_failed")
        return RunInformationSourceAndInitiateWeakSupervisionByLabelingTaskId(ok=True)


class WeakSupervisionMutation(graphene.ObjectType):
    initiate_weak_supervision_by_project_id = InitiateWeakSupervisionByProjectId.Field()
    run_heuristic_then_trigger_weak_supervision = (
        RunInformationSourceAndInitiateWeakSupervisionByLabelingTaskId.Field()
    )
