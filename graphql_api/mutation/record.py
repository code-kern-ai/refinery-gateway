import graphene

from controller.auth import manager as auth
from submodules.model.enums import InformationSourceType
from util import notification
from controller.record import manager as record_manager
from controller.embedding import manager as embedding_manager
from controller.project import manager as project_manager
from controller.payload import manager as payload_manager
from controller.zero_shot import manager as zero_shot_manager


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
        record_id = graphene.ID()

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, record_id: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)

        print("FullWorkflowRecord")

        record = record_manager.get_record(project_id, record_id)
        if record is None:
            raise Exception("Record not found")
        project = project_manager.get_project(project_id)

        # TODO 5: tokenize record

        # TODO 4: enrich attributes

        # TODO 1: enrich embedding
        embedding_dict = {}
        for embedding in project.embeddings:
            embedding_vector = embedding_manager.create_single_embeddings(
                project_id, embedding.id, record_id
            )
            embedding_dict[embedding.name] = embedding_vector

        # TODO 2: call all heuristics in a single container
        noisy_labels = []
        for information_source in project.information_sources:
            print(information_source.name)
            if information_source.type == InformationSourceType.ACTIVE_LEARNING.value:
                labels = payload_manager.get_active_learning_on_1_record(
                    project_id, information_source.id, record_id
                )
                if len(labels) > 0:
                    labels = labels[record_id]
                    noisy_labels.append(
                        {
                            "information_source_id": str(information_source.id),
                            "labels": labels[1],
                            "confidence": labels[0],
                        }
                    )
            elif (
                information_source.type == InformationSourceType.LABELING_FUNCTION.value
            ):
                labels = payload_manager.get_labeling_function_on_1_record(
                    project_id, information_source.id, record_id
                )
                if len(labels) > 0:
                    labels = labels[record_id]
                    noisy_labels.append(
                        {
                            "information_source_id": str(information_source.id),
                            "labels": labels[1],
                            "confidence": labels[0],
                        }
                    )
            elif information_source.type == InformationSourceType.ZERO_SHOT.value:
                labels = zero_shot_manager.get_zero_shot_1_record(
                    project_id, str(information_source.id), record_id
                )
                # TODO: for some reason, the output of the zero-shot model is always None (even though the model is working)
                # TODO: integrate at later point in time

        print(noisy_labels)
        # TODO 3: call weak supervision for this one record

        return FullWorkflowRecord(ok=True)


class RecordMutation(graphene.ObjectType):
    delete_record = DeleteRecord.Field()
    full_workflow_record = FullWorkflowRecord.Field()
