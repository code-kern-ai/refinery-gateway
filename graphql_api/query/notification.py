from typing import List, Optional

import graphene

from controller.auth import manager as auth
from graphql_api.types import Notification
from submodules.model.enums import NotificationType
from submodules.model.business_objects.notification import (
    get_notifications_by_user_id,
    get_filtered_notification,
)


class NotificationQuery(graphene.ObjectType):
    notifications_by_user_id = graphene.Field(
        graphene.List(Notification),
    )

    notifications = graphene.Field(
        graphene.List(Notification),
        project_filter=graphene.List(graphene.ID, required=False),
        level_filter=graphene.List(graphene.String, required=False),
        type_filter=graphene.List(graphene.String, required=False),
        user_filter=graphene.Boolean(required=False),
        limit=graphene.Int(required=False),
    )

    notification_types = graphene.Field(
        graphene.List(graphene.String),
    )

    def resolve_notifications_by_user_id(self, info, **kwargs) -> List[Notification]:
        auth.check_demo_access(info)
        user = auth.get_user_by_info(info)
        return get_notifications_by_user_id(user.id)

    def resolve_notifications(
        self,
        info,
        project_filter: Optional[List[str]] = None,
        level_filter: Optional[List[str]] = None,
        type_filter: Optional[List[str]] = None,
        user_filter: Optional[bool] = True,
        limit: Optional[int] = 50,
    ) -> List[Notification]:
        auth.check_demo_access(info)

        if project_filter is None:
            project_filter = []
        if level_filter is None:
            level_filter = []
        if type_filter is None:
            type_filter = []

        for project_id in project_filter:
            auth.check_project_access(info, project_id)

        user = auth.get_user_by_info(info)
        return get_filtered_notification(
            user, project_filter, level_filter, type_filter, user_filter, limit
        )

    def resolve_notification_types(self, info) -> List[str]:
        auth.check_demo_access(info)
        return [notification_type.name for notification_type in NotificationType]
