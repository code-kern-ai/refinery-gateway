from typing import List

from controller.auth import manager as auth
from controller.information_source import manager
from graphql_api.types import InformationSource
import graphene


class InformationSourceQuery(graphene.ObjectType):

    information_source_by_source_id = graphene.Field(
        InformationSource,
        project_id=graphene.ID(required=True),
        information_source_id=graphene.ID(required=True),
    )

    information_sources_by_project_id = graphene.Field(
        graphene.List(InformationSource),
        project_id=graphene.ID(required=True),
    )

    information_sources_overview_data = graphene.Field(
        graphene.JSONString,
        project_id=graphene.ID(required=True),
    )

    def resolve_information_source_by_source_id(
        self, info, project_id: str, information_source_id: str
    ) -> InformationSource:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return manager.get_information_source(project_id, information_source_id)

    def resolve_information_sources_by_project_id(
        self, info, project_id: str
    ) -> List[InformationSource]:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return manager.get_all_information_sources(project_id)

    def resolve_information_sources_overview_data(
        self,
        info,
        project_id: str,
    ) -> str:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return manager.get_overview_data(project_id)
