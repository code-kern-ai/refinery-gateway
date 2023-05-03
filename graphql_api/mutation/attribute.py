from typing import Optional
from controller.auth import manager as auth
import graphene
from controller.attribute import manager

from controller.task_queue import manager as task_queue_manager
from submodules.model.enums import TaskType


class CreateUserAttribute(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        name = graphene.String(required=True)
        data_type = graphene.String(required=True)

    ok = graphene.Boolean()
    attribute_id = graphene.ID()

    def mutate(self, info, project_id: str, name: str, data_type: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        attribute = manager.create_user_attribute(project_id, name, data_type)
        return CreateUserAttribute(ok=True, attribute_id=attribute.id)


class UpdateAttribute(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        attribute_id = graphene.ID(required=True)
        data_type = graphene.String()
        is_primary_key = graphene.Boolean()
        name = graphene.String()
        source_code = graphene.String()
        visibility = graphene.String()

    ok = graphene.Boolean()

    def mutate(
        self,
        info,
        project_id: str,
        attribute_id: str,
        data_type: Optional[str] = None,
        is_primary_key: Optional[bool] = None,
        name: Optional[str] = None,
        source_code: Optional[str] = None,
        visibility: Optional[str] = None,
    ):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.update_attribute(
            project_id,
            attribute_id,
            data_type,
            is_primary_key,
            name,
            source_code,
            visibility,
        )
        return UpdateAttribute(ok=True)


class DeleteUserAttribute(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        attribute_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, attribute_id: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.delete_attribute(project_id, attribute_id)
        return DeleteUserAttribute(ok=True)


class AddRunningId(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        attribute_name = graphene.ID(required=False)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, attribute_name: str = "running_id"):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user = auth.get_user_by_info(info)
        manager.add_running_id(str(user.id), project_id, attribute_name)
        return AddRunningId(ok=True)


class CalculateUserAttributeAllRecords(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        attribute_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, attribute_id: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user_id = auth.get_user_by_info(info).id
        task_queue_manager.add_task(
            project_id,
            TaskType.ATTRIBUTE_CALCULATION,
            user_id,
            {
                "attribute_id": attribute_id,
            },
            True,
        )

        return CalculateUserAttributeAllRecords(ok=True)


class AttributeMutation(graphene.ObjectType):
    create_user_attribute = CreateUserAttribute.Field()
    delete_user_attribute = DeleteUserAttribute.Field()
    update_attribute = UpdateAttribute.Field()
    add_running_id = AddRunningId.Field()
    calculate_user_attribute_all_records = CalculateUserAttributeAllRecords.Field()
