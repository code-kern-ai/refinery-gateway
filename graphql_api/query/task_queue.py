from typing import List

import graphene


from graphql_api.types import TaskQueue

from controller.task_queue import manager
from controller.auth import manager as auth


class TaskQueueQuery(graphene.ObjectType):
    queued_tasks = graphene.List(
        TaskQueue,
        project_id=graphene.ID(required=True),
        task_type=graphene.String(required=True),
    )

    def resolve_queued_tasks(
        self, info, project_id: str, task_type: str
    ) -> List[TaskQueue]:
        auth.check_project_access(info, project_id)
        return manager.get_all_waiting_by_type(project_id, task_type)
