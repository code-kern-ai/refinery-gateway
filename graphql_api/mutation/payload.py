import graphene
from controller.auth import manager as auth
from controller.auth.manager import get_user_by_info

from controller.task_queue import manager as task_queue_manager
from submodules.model.enums import TaskType
from submodules.model.business_objects import information_source
from submodules.model import enums


class CreatePayload(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID()
        information_source_id = graphene.ID()

    queue_id = graphene.ID()

    def mutate(self, info, project_id: str, information_source_id: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user = get_user_by_info(info)
        information_source_item = information_source.get(
            project_id, information_source_id
        )
        if (
            information_source_item.type
            == enums.InformationSourceType.CROWD_LABELER.value
        ):
            return CreatePayload(None)
        priority = (
            information_source_item.type != enums.InformationSourceType.ZERO_SHOT.value
        )

        queue_id, _ = task_queue_manager.add_task(
            project_id,
            TaskType.INFORMATION_SOURCE,
            user.id,
            {
                "information_source_id": information_source_id,
                "source_type": information_source_item.type,
            },
            priority=priority,
        )
        return CreatePayload(queue_id)


class PayloadMutation(graphene.ObjectType):
    create_payload = CreatePayload.Field()
