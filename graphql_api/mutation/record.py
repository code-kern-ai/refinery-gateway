import graphene

from controller.auth import manager as auth
from submodules.model.enums import InformationSourceType
from util import notification
from controller.record import manager as record_manager
from controller.embedding import manager as embedding_manager
from controller.project import manager as project_manager
from controller.payload import manager as payload_manager


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
        record = record_manager.get_record(project_id, record_id)
        project = project_manager.get_project(project_id)

        # TODO 4: enrich attributes

        # TODO 1: enrich embedding
        embedding_dict = {}
        for embedding in project.embeddings:
            embedding_vector = embedding_manager.create_single_embeddings(
                project_id, embedding.id, record_id
            )
            embedding_dict[embedding.name] = embedding_vector

        # TODO 2: call all heuristics in a single container
        for information_source in project.information_sources:
            if information_source.type == InformationSourceType.ACTIVE_LEARNING.value:
                print(information_source.name)
                payload_manager.get_active_learning_on_1_record(
                    project_id, information_source.id, record_id
                )

        # TODO 3: call weak supervision for this one record

        return FullWorkflowRecord(ok=True)


class RecordMutation(graphene.ObjectType):
    delete_record = DeleteRecord.Field()
    full_workflow_record = FullWorkflowRecord.Field()
