import graphene

from controller.auth import manager as auth
from graphql_api.types import AdminMessage
from controller.admin_message import manager


class AdminMessageQuery(graphene.ObjectType):
    all_admin_messages = graphene.Field(
        graphene.List(AdminMessage),
    )

    all_active_admin_messages = graphene.Field(
        graphene.List(AdminMessage),
    )

    def resolve_all_admin_messages(self, info) -> AdminMessage:
        auth.check_demo_access(info)
        auth.check_admin_access(info)
        return manager.get_all_admin_messages()

    def resolve_all_active_admin_messages(self, info) -> AdminMessage:
        auth.check_demo_access(info)
        return manager.get_all_active_admin_messages()
