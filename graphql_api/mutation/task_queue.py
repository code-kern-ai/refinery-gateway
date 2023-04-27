import graphene

from controller.auth import manager as auth
from util import notification
from controller.task_queue import manager


class DeleteFromTaskQueue(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID()
        task_id = graphene.ID()

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, task_id: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.remove_task_from_queue(project_id, task_id)
        return DeleteFromTaskQueue(ok=True)


class TaskQueueMutation(graphene.ObjectType):
    delete_from_task_queue = DeleteFromTaskQueue.Field()
