from controller.auth import manager as auth
from controller.embedding import manager
from controller.auth.manager import get_user_by_info
from util import notification
import graphene


class CreateAttributeLevelEmbedding(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        attribute_id = graphene.ID(required=True)
        embedding_handle = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, attribute_id: str, embedding_handle: str):
        auth.check_project_access(info, project_id)
        user = get_user_by_info(info)
        manager.create_attribute_level_embedding(
            project_id, user.id, attribute_id, embedding_handle
        )
        return CreateAttributeLevelEmbedding(ok=True)


class CreateTokenLevelEmbedding(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        attribute_id = graphene.ID(required=True)
        embedding_handle = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, attribute_id: str, embedding_handle: str):
        auth.check_project_access(info, project_id)
        user = get_user_by_info(info)
        manager.create_token_level_embedding(
            project_id, user.id, attribute_id, embedding_handle
        )
        return CreateTokenLevelEmbedding(ok=True)


class DeleteEmbedding(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        embedding_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, embedding_id: str):
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
