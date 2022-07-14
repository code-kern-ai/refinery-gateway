from typing import Optional, List

import graphene

from controller.auth import manager as auth
from graphql_api.types import Record
from submodules.model import enums, events
from graphql_api import types
from util import doc_ock, notification
from controller.record_label_association import manager
from controller.project import manager as project_manager


class CreateClassificationAssociation(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID()
        record_id = graphene.ID()
        label_id = graphene.ID()
        labeling_task_id = graphene.ID()
        as_gold_star = graphene.Boolean(required=False)

    ok = graphene.Boolean()
    record = graphene.Field(lambda: Record)

    def mutate(
        self,
        info,
        project_id: str,
        record_id: str,
        label_id: str,
        labeling_task_id: str,
        as_gold_star: Optional[bool] = None,
    ):
        auth.check_project_access(info, project_id)
        user = auth.get_user_by_info(info)
        record = manager.create_classification_label(
            project_id, user.id, record_id, label_id, labeling_task_id, as_gold_star
        )

        # this below seems not optimal positioned here
        project = project_manager.get_project(project_id)
        doc_ock.post_event(
            user,
            events.AddLabelsToRecord(
                ProjectName=f"{project.name}-{project.id}",
                Type=enums.LabelingTaskType.CLASSIFICATION.value,
            ),
        )
        notification.send_organization_update(project_id, f"rla_created:{record_id}")

        return CreateClassificationAssociation(ok=True, record=record)


class CreateExtractionAssociation(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID()
        record_id = graphene.ID()
        labeling_task_id = graphene.ID()
        label_id = graphene.ID()
        token_start_index = graphene.Int()
        token_end_index = graphene.Int()
        value = graphene.String()
        as_gold_star = graphene.Boolean(required=False)

    ok = graphene.Boolean()
    record = graphene.Field(lambda: Record)

    def mutate(
        self,
        info,
        project_id: str,
        record_id: str,
        labeling_task_id: str,
        label_id: str,
        token_start_index: int,
        token_end_index: int,
        value: str,
        as_gold_star: Optional[bool] = None,
    ):
        auth.check_project_access(info, project_id)
        user = auth.get_user_by_info(info)
        record = manager.create_extraction_label(
            project_id,
            user.id,
            record_id,
            labeling_task_id,
            label_id,
            token_start_index,
            token_end_index,
            value,
            as_gold_star,
        )
        project = project_manager.get_project(project_id)
        doc_ock.post_event(
            user,
            events.AddLabelsToRecord(
                ProjectName=f"{project.name}-{project.id}",
                Type=enums.LabelingTaskType.INFORMATION_EXTRACTION.value,
            ),
        )
        notification.send_organization_update(project_id, f"rla_created:{record_id}")
        return CreateExtractionAssociation(ok=True, record=record)


class SetGoldStarAnnotationForTask(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID()
        record_id = graphene.ID()
        labeling_task_id = graphene.ID()
        gold_user_id = graphene.ID()

    ok = graphene.Boolean()

    def mutate(
        self,
        info,
        project_id: str,
        record_id: str,
        labeling_task_id: str,
        gold_user_id: str,
    ):
        auth.check_project_access(info, project_id)
        user = auth.get_user_by_info(info)
        task_type = manager.create_gold_star_association(
            project_id, record_id, labeling_task_id, gold_user_id, user.id
        )

        project = project_manager.get_project(project_id)
        doc_ock.post_event(
            user,
            events.AddLabelsToRecord(
                ProjectName=f"{project.name}-{project.id}", Type=task_type,
            ),
        )
        notification.send_organization_update(project_id, f"rla_created:{record_id}")

        return SetGoldStarAnnotationForTask(ok=True)


class DeleteRecordLabelAssociationByIds(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID()
        record_id = graphene.ID()
        association_ids = graphene.List(graphene.ID)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, record_id: str, association_ids: List[str]):
        auth.check_project_access(info, project_id)
        manager.delete_record_label_association(project_id, record_id, association_ids)
        notification.send_organization_update(project_id, f"rla_deleted:{record_id}")

        return DeleteRecordLabelAssociationByIds(ok=True)


class DeleteGoldStarAssociationForTask(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID()
        record_id = graphene.ID()
        labeling_task_id = graphene.ID()

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, record_id: str, labeling_task_id: str):
        auth.check_project_access(info, project_id)
        user = auth.get_user_by_info(info)
        manager.delete_gold_star_association(
            project_id, user.id, record_id, labeling_task_id
        )
        notification.send_organization_update(project_id, f"rla_deleted:{record_id}")

        return DeleteGoldStarAssociationForTask(ok=True)


##update logic only to be run once
class UpdateRlaIsValidManual(graphene.Mutation):
    class Arguments:
        execute = graphene.Boolean(required=False)

    ok = graphene.Boolean()

    def mutate(self, info, execute: Optional[bool] = False):
        if execute:
            manager.update_is_valid_manual_label_for_all()

        return DeleteGoldStarAssociationForTask(ok=True)


class RecordLabelAssociationMutation(graphene.ObjectType):
    add_classification_labels_to_record = CreateClassificationAssociation.Field()
    add_extraction_label_to_record = CreateExtractionAssociation.Field()
    set_gold_star_annotation_for_task = SetGoldStarAnnotationForTask.Field()
    delete_record_label_association_by_ids = DeleteRecordLabelAssociationByIds.Field()
    remove_gold_star_annotation_for_task = DeleteGoldStarAssociationForTask.Field()
    update_rla_is_valid_manual = UpdateRlaIsValidManual.Field()
