import graphene
from controller.auth import manager as auth
from controller.auth.manager import get_user_by_info
from controller.embedder_payload import manager
from graphql_api.types import EmbedderPayload


class CreateEmbedderPayload(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID()
        embedder_id = graphene.ID()

    payload = graphene.Field(EmbedderPayload)

    def mutate(self, info, project_id: str, embedder_id: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user = get_user_by_info(info)
        payload = manager.create_payload(info, project_id, embedder_id, user.id)
        return CreateEmbedderPayload(payload)


class EmbedderPayloadMutation(graphene.ObjectType):
    create_embedder_payload = CreateEmbedderPayload.Field()
