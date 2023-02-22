import graphene
from graphql_api.types import User
from controller.user import manager
from controller.auth import manager as auth


class UserQuery(graphene.ObjectType):

    active_users = graphene.Field(
        graphene.List(User),
        minutes_range=graphene.Int(required=False),
    )

    def resolve_active_users(self, info, minutes_interval: int):
        auth.check_admin_access(info)
        return manager.get_active_users(minutes_interval)
