from datetime import datetime
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

    link_locked = graphene.Field(
        graphene.Boolean,
        project_id=graphene.ID(required=True),
        link_route=graphene.String(required=True),
    )

    link_data_outdated = graphene.Field(
        graphene.Boolean,
        project_id=graphene.ID(required=True),
        link_route=graphene.String(required=True),
        last_requested_at=graphene.DateTime(required=True),
    )

    def resolve_access_link(
        self, info, project_id: str, link_id: str
    ) -> List[DataSlice]:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return manager.get(link_id)

    def resolve_link_locked(
        self, info, project_id: str, link_route: str
    ) -> List[DataSlice]:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return manager.check_link_locked(project_id, link_route)

    def resolve_link_data_outdated(
        self, info, project_id: str, link_route: str, last_requested_at: datetime
    ) -> List[DataSlice]:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        naive_time = last_requested_at.replace(tzinfo=None)
        return manager.check_link_data_outdated(project_id, link_route, naive_time)
