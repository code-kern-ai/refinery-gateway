import graphene

from controller.auth import manager as auth
from graphql_api.types import LabelingTask
from controller.labeling_task import manager


class LabelingTaskQuery(graphene.ObjectType):
    labeling_task_by_labeling_task_id = graphene.Field(
        LabelingTask,
        project_id=graphene.ID(required=True),
        labeling_task_id=graphene.ID(required=True),
    )

    def resolve_labeling_task_by_labeling_task_id(
        self, info, project_id: str, labeling_task_id: str
    ) -> LabelingTask:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return manager.get_labeling_task(project_id, labeling_task_id)
