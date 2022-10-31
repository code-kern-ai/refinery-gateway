from typing import Any, Dict
import graphene
import json
import uuid

from controller.auth import manager as auth
from submodules.model.enums import InformationSourceType
from util import notification
from controller.record import manager as record_manager
from controller.embedding import manager as embedding_manager
from controller.project import manager as project_manager
from controller.payload import manager as payload_manager
from graphql_api import types


class DeleteRecord(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID()
        record_id = graphene.ID()

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, record_id: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.delete_record(project_id, record_id)
        notification.send_organization_update(project_id, f"record_deleted:{record_id}")
        return DeleteRecord(ok=True)


class FullWorkflowRecord(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID()
        embedding_name = graphene.String()
        active_learner_name = graphene.String()
        record_data = graphene.JSONString()

    response = graphene.Field(types.InferenceResult)

    def mutate(
        self,
        info,
        project_id: str,
        embedding_name: str,
        active_learner_name: str,
        record_data: Dict[str, Any],
    ):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)

        project = project_manager.get_project(project_id)

        record = record_manager.create_record(project_id, record_data)

        found_embedding = False  # only for the beta version
        for embedding in project.embeddings:
            if embedding.name == embedding_name:  # only for the beta version
                embedding_manager.create_single_embedding(
                    project_id, embedding.id, record.id
                )
                found_embedding = True

        if not found_embedding:
            raise Exception("Embedding not found")

        results = []
        for labeling_task in project.labeling_tasks:
            prediction_task = None
            for information_source in labeling_task.information_sources:
                if (
                    information_source.name == active_learner_name
                ):  # only for the beta version
                    if (
                        information_source.type
                        == InformationSourceType.ACTIVE_LEARNING.value
                    ):
                        labels = payload_manager.get_active_learning_on_1_record(
                            project_id, str(information_source.id), str(record.id)
                        )
                        if len(labels) > 0:
                            labels = labels[str(record.id)]
                            prediction_task = types.InferencePredictionItem(
                                label=labels[1],
                                confidence=labels[0],
                            )

                    elif (
                        information_source.type
                        == InformationSourceType.LABELING_FUNCTION.value
                    ):
                        pass
                    elif (
                        information_source.type == InformationSourceType.ZERO_SHOT.value
                    ):
                        pass
            if prediction_task is not None:
                results.append(
                    types.InferenceItem(
                        labeling_task=labeling_task.name,
                        prediction=prediction_task,
                    )
                )

            response = types.InferenceResult(results=results)

        if found_embedding:
            embedding_manager.delete_single_embedding(
                project_id, embedding.id, record.id
            )

        record_manager.delete_record(project_id, record.id)

        return FullWorkflowRecord(response=response)


class RecordMutation(graphene.ObjectType):
    delete_record = DeleteRecord.Field()
    full_workflow_record = FullWorkflowRecord.Field()
