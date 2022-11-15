import graphene

from controller.auth import manager as auth
from graphql_api.types import LabelingTask
from controller.labeling_task_label import manager


class LabelingTaskLabelQuery(graphene.ObjectType):
    check_rename_label = graphene.Field(
        graphene.JSONString,
        project_id=graphene.ID(required=True),
        label_id=graphene.ID(required=True),
        new_name=graphene.String(required=True),
    )

    def resolve_check_rename_label(
        self, info, project_id: str, label_id: str, new_name: str
    ) -> LabelingTask:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return manager.check_rename_label(project_id, label_id, new_name)
