from controller import embedder
import graphene
from typing import Optional

from controller.auth import manager as auth
from controller.auth.manager import get_user_by_info
from controller.embedder import manager
from graphql_api.types import Embedder
from util import notification


class CreateEmbedder(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        name = graphene.String(required=True)
        type = graphene.String(required=True)
        source_code = graphene.String()
        description = graphene.String()

    embedder = graphene.Field(Embedder)

    def mutate(
        self,
        info,
        project_id: str,
        name: str,
        type: str,
        source_code: Optional[str] = None,
        description: Optional[str] = None,
    ):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user = get_user_by_info(info)
        embedder = manager.create_embedder(
            project_id, user.id, name, source_code, description, type
        )
        notification.send_organization_update(project_id, f"embedder_created")
        return CreateEmbedder(embedder=embedder)


class DeleteEmbedder(graphene.Mutation):
    class Arguments:
        information_source_id = graphene.ID(required=True)
        project_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, embedder_id: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.delete_embedder(project_id, embedder_id)
        notification.send_organization_update(
            project_id, f"embedder_deleted:{embedder_id}"
        )
        return DeleteEmbedder(ok=True)


class UpdateEmbedder(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        embedder_id = graphene.ID(required=True)
        code = graphene.String()
        description = graphene.String()
        name = graphene.String()

    ok = graphene.Boolean()

    def mutate(
        self,
        info,
        project_id: str,
        embedder_id: str,
        code: Optional[str] = None,
        description: Optional[str] = None,
        name: Optional[str] = None,
    ):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.update_embedder(project_id, embedder_id, code, description, name)
        user = auth.get_user_by_info(info)
        notification.send_organization_update(
            project_id, f"embedder_updated:{embedder_id}:{user.id}"
        )
        return UpdateEmbedder(ok=True)


class EmbedderMutation(graphene.ObjectType):
    create_embedder = CreateEmbedder.Field()
    delete_embedder = DeleteEmbedder.Field()
    update_embedder = UpdateEmbedder.Field()
