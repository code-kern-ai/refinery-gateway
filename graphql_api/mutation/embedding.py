from controller.auth import manager as auth
from controller.embedding import manager
from controller.auth.manager import get_user_by_info
from util import notification
import graphene

from controller.task_queue import manager as task_queue_manager
from submodules.model.enums import TaskType, EmbeddingType


class CreateAttributeLevelEmbedding(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        attribute_id = graphene.ID(required=True)
        embedding_handle = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, attribute_id: str, embedding_handle: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user = get_user_by_info(info)
        embedding_type = EmbeddingType.ON_ATTRIBUTE.value
        task_queue_manager.add_task(
            project_id,
            TaskType.EMBEDDING,
            user.id,
            {
                "embedding_type": embedding_type,
                "attribute_id": attribute_id,
                "embedding_handle": embedding_handle,
                "embedding_name": manager.get_embedding_name(
                    project_id, attribute_id, embedding_type, embedding_handle
                ),
            },
        )
        notification.send_organization_update(
            project_id=project_id, message="embedding:queued"
        )
        return CreateAttributeLevelEmbedding(ok=True)


class CreateTokenLevelEmbedding(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        attribute_id = graphene.ID(required=True)
        embedding_handle = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, attribute_id: str, embedding_handle: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user = get_user_by_info(info)
        embedding_type = EmbeddingType.ON_TOKEN.value
        task_queue_manager.add_task(
            project_id,
            TaskType.EMBEDDING,
            user.id,
            {
                "embedding_type": embedding_type,
                "attribute_id": attribute_id,
                "embedding_handle": embedding_handle,
                "embedding_name": manager.get_embedding_name(
                    project_id, attribute_id, embedding_type, embedding_handle
                ),
            },
        )
        notification.send_organization_update(
            project_id=project_id, message="embedding:queued"
        )
        return CreateTokenLevelEmbedding(ok=True)


class DeleteEmbedding(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        embedding_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, embedding_id: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.delete_embedding(project_id, embedding_id)
        notification.send_organization_update(
            project_id, f"embedding_deleted:{embedding_id}"
        )
        return DeleteEmbedding(ok=True)


class EmbeddingMutation(graphene.ObjectType):
    create_attribute_level_embedding = CreateAttributeLevelEmbedding.Field()
    create_token_level_embedding = CreateTokenLevelEmbedding.Field()
    delete_embedding = DeleteEmbedding.Field()
