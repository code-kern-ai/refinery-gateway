from typing import List

import graphene
import util.user_activity
from controller.auth import manager as auth
from graphql_api.types import ToolTip, UserActivityWrapper
from util import tooltip
from controller.misc import config_service, manager


class MiscQuery(graphene.ObjectType):

    tooltip = graphene.Field(
        ToolTip,
        key=graphene.String(required=True),
    )

    all_users_activity = graphene.Field(
        graphene.List(UserActivityWrapper),
    )

    is_managed = graphene.Field(graphene.Boolean)

    is_demo = graphene.Field(graphene.Boolean)

    is_admin = graphene.Field(graphene.Boolean)

    get_black_white_demo = graphene.Field(graphene.JSONString)

    def resolve_tooltip(self, info, key: str) -> ToolTip:
        return tooltip.resolve_tooltip(key)

    def resolve_all_users_activity(self, info) -> List[UserActivityWrapper]:
        auth.check_is_demo(info)
        auth.check_admin_access(info)
        return util.user_activity.resolve_all_users_activity()

    def resolve_is_managed(self, info) -> bool:
        return manager.check_is_managed()

    def resolve_is_demo(self, info) -> bool:
        return config_service.get_config_value("is_demo")

    def resolve_is_admin(self, info) -> bool:
        return auth.check_is_admin(info.context["request"])

    def resolve_get_black_white_demo(self, info) -> str:
        return manager.get_black_white_demo()
