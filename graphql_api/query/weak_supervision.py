import graphene

from controller.auth import manager as auth
from graphql_api.types import WeakSupervisionTask
from submodules.model.business_objects import weak_supervision


class WeakSupervisionQuery(graphene.ObjectType):
    current_weak_supervision_run = graphene.Field(
        WeakSupervisionTask,
        project_id=graphene.ID(required=True),
    )

    def resolve_current_weak_supervision_run(
        self, info, project_id: str
    ) -> WeakSupervisionTask:
        auth.check_is_demo(info)
        auth.check_project_access(info, project_id)
        return weak_supervision.get_current_weak_supervision_run(project_id)
