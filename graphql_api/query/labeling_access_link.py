from typing import List, Optional

import graphene

from controller.auth import manager as auth
from graphql_api.types import DataSlice, LabelingAccessLink
from controller.labeling_access_link import manager


class LabelingAccessLinkQuery(graphene.ObjectType):

    access_link = graphene.Field(
        LabelingAccessLink,
        project_id=graphene.ID(required=True),
        link_id=graphene.ID(required=True),
    )

    def resolve_access_link(
        self, info, project_id: str, link_id: str
    ) -> List[DataSlice]:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return manager.get(link_id)
