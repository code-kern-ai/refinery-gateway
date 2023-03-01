import graphene

from controller.auth import manager as auth
from graphql_api.types import AdminMessage
from controller.admin_message import manager


class AdminMessageQuery(graphene.ObjectType):
    all_admin_messages = graphene.Field(
        graphene.List(AdminMessage), limit=graphene.Int()
    )

    all_active_admin_messages = graphene.Field(
        graphene.List(AdminMessage), limit=graphene.Int()
    )

    def resolve_all_admin_messages(self, info, limit: int = 100) -> AdminMessage:
        auth.check_demo_access(info)
        auth.check_admin_access(info)
        return manager.get_all_admin_messages(limit)

    def resolve_all_active_admin_messages(self, info, limit: int = 100) -> AdminMessage:
        auth.check_demo_access(info)
        return manager.get_and_check_all_active_admin_messages(limit)
