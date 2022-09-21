from datetime import datetime
import json
from typing import List, Optional

import graphene

from controller.auth import manager as auth
from graphql_api.types import DataSlice, LabelingAccessLink
from controller.labeling_access_link import manager
from submodules.model import enums
from submodules.model.business_objects import (
    information_source as is_manager,
    user as user_manager,
)


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

    available_links = graphene.Field(
        graphene.List(LabelingAccessLink),
        project_id=graphene.ID(required=True),
        # only to fill for engeneers testing the labeling view
        assumed_role=graphene.String(required=False),
        # only to fill for engeneers testing the labeling view as annotator
        assumed_heuristic_id=graphene.ID(required=False),
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

    def resolve_available_links(
        self,
        info,
        project_id: str,
        assumed_role: Optional[str] = None,
        assumed_heuristic_id: Optional[str] = None,
    ) -> List[DataSlice]:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)

        if assumed_heuristic_id:
            is_item = is_manager.get(project_id, assumed_heuristic_id)
            if (
                not is_item
                or is_item.type != enums.InformationSourceType.CROWD_LABELER.value
            ):
                raise ValueError("Unknown heuristic id")
            settings = json.loads(is_item.source_code)
            user = user_manager.get(settings["annotator_id"])
        else:
            user = auth.get_user_by_info(info)

        user_role = assumed_role if assumed_role else user.role
        return manager.get_by_all_by_user_id(project_id, str(user.id), user_role)
