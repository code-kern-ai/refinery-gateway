import graphene
from controller.auth import manager as auth
from controller.monitor import manager


class CancelAllRunningTasks(graphene.Mutation):
    ok = graphene.Boolean()

    def mutate(self, info):
        auth.check_admin_access(info)
        manager.cancel_all_running_tasks()
        return CancelAllRunningTasks(ok=True)


class MonitorMutation(graphene.ObjectType):
    cancel_all_running_tasks = CancelAllRunningTasks.Field()
