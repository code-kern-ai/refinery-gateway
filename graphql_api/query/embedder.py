from typing import List

from controller.auth import manager as auth
from controller.embedder import manager
from graphql_api.types import Embedder
import graphene


class EmbedderQuery(graphene.ObjectType):

    embedder_by_embedder_id = graphene.Field(
        Embedder,
        project_id=graphene.ID(required=True),
        embedder_id=graphene.ID(required=True),
    )

    embedders_by_project_id = graphene.Field(
        graphene.List(Embedder),
        project_id=graphene.ID(required=True),
    )

    embedders_overview_data = graphene.Field(
        graphene.JSONString,
        project_id=graphene.ID(required=True),
    )

    def resolve_embedder_by_embedder_id(
        self, info, project_id: str, embedder_id: str
    ) -> Embedder:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return manager.get_embedder(project_id, embedder_id)

    def resolve_embedders_by_project_id(self, info, project_id: str) -> List[Embedder]:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return manager.get_all_embedders(project_id)

    def resolve_embedders_overview_data(
        self,
        info,
        project_id: str,
    ) -> str:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return manager.get_overview_data(project_id)
