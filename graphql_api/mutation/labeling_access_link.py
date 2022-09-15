from typing import Any, Dict, List, Optional

from controller.auth import manager as auth
import graphene
from submodules.model import enums
from controller.labeling_access_link import manager
from graphql_api.types import LabelingAccessLink


class GenerateAccessLink(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        type = graphene.String(required=True)
        id = graphene.ID(required=True)

    # id = graphene.ID()
    link = graphene.Field(LabelingAccessLink)

    def mutate(
        self,
        info,
        project_id: str,
        type: str,
        id: str,
    ):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user = auth.get_user_by_info(info)
        try:
            link_type_parsed = enums.LinkTypes[type.upper()]
        except KeyError:
            raise ValueError(f"Invalid LinkTypes: {type}")

        if link_type_parsed == enums.LinkTypes.HEURISTIC:
            link = manager.generate_heuristic_access_link(project_id, user.id, id)
        elif link_type_parsed == enums.LinkTypes.DATA_SLICE:
            print("not yet supported")
        return GenerateAccessLink(link=link)


class RemoveAccessLink(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        link_id = graphene.ID(required=True)

    # id = graphene.ID()
    ok = graphene.Boolean()

    def mutate(
        self,
        info,
        project_id: str,
        link_id: str,
    ):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.remove(link_id)
        return GenerateAccessLink(ok=True)


class LabelingAccessLinkMutation(graphene.ObjectType):
    generate_access_link = GenerateAccessLink.Field()
    remove_access_link = RemoveAccessLink.Field()
