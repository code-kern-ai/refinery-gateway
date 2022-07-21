import graphene
from util import notification
from controller.zero_shot import manager
from controller.auth import manager as auth_manager


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
        auth_manager.check_is_demo(info)
        auth_manager.check_project_access(info, project_id)
        user_id = auth_manager.get_user_id_by_info(info)
        manager.start_zero_shot_for_project_thread(
            project_id, information_source_id, user_id
        )

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
        auth_manager.check_is_demo(info)
        auth_manager.check_project_access(info, project_id)
        user_id = auth_manager.get_user_id_by_info(info)
        zero_shot_id = manager.create_zero_shot_information_source(
            user_id, project_id, target_config, labeling_task_id, attribute_id
        )
        notification.send_organization_update(project_id, f"information_source_created")

        return CreateZeroShotInformationSource(id=zero_shot_id)


class ZeroShotMutation(graphene.ObjectType):
    zero_shot_project = ZeroShotProject.Field()
    create_zero_shot_information_source = CreateZeroShotInformationSource.Field()
