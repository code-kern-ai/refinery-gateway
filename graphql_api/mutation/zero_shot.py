import graphene
from util import notification
from controller.zero_shot import manager
from controller.auth import manager as auth_manager


from controller.task_queue import manager as task_queue_manager
from submodules.model.enums import TaskType


class ZeroShotProject(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        information_source_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(
        self,
        info,
        project_id: str,
        information_source_id: str,
    ):
        auth_manager.check_demo_access(info)
        auth_manager.check_project_access(info, project_id)
        user_id = auth_manager.get_user_id_by_info(info)

        task_queue_manager.add_task(
            project_id,
            TaskType.INFORMATION_SOURCE,
            user_id,
            {
                "information_source_id": information_source_id,
            },
        )
        return ZeroShotProject(ok=True)


class CancelZeroShotRun(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        information_source_id = graphene.ID(required=True)
        payload_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(
        self,
        info,
        project_id: str,
        information_source_id: str,
        payload_id: str,
    ):
        auth_manager.check_demo_access(info)
        auth_manager.check_project_access(info, project_id)

        manager.cancel_zero_shot_run(project_id, information_source_id, payload_id)

        return ZeroShotProject(ok=True)


class CreateZeroShotInformationSource(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        target_config = graphene.String(required=True)
        labeling_task_id = graphene.ID(required=True)
        attribute_id = graphene.ID(required=False)

    id = graphene.ID()

    def mutate(
        self,
        info,
        project_id: str,
        target_config: str,
        labeling_task_id: str,
        attribute_id: str = "",
    ):
        auth_manager.check_demo_access(info)
        auth_manager.check_project_access(info, project_id)
        user_id = auth_manager.get_user_id_by_info(info)
        zero_shot_id = manager.create_zero_shot_information_source(
            user_id, project_id, target_config, labeling_task_id, attribute_id
        )
        notification.send_organization_update(
            project_id, f"information_source_created:{zero_shot_id}"
        )

        return CreateZeroShotInformationSource(id=zero_shot_id)


class ZeroShotMutation(graphene.ObjectType):
    zero_shot_project = ZeroShotProject.Field()
    create_zero_shot_information_source = CreateZeroShotInformationSource.Field()
    cancel_zero_shot_run = CancelZeroShotRun.Field()
