import graphene
from graphql_api.types import Task
from controller.auth import manager as auth
from controller.monitor import manager


class MonitorQuery(graphene.ObjectType):

    all_tasks = graphene.Field(
        graphene.List(Task),
        only_running=graphene.Boolean()
    )

    def resolve_all_tasks(self, info, only_running: bool = None):
        auth.check_admin_access(info)
        return manager.monitor_all_tasks(only_running=only_running)
