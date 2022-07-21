from typing import Any

from controller.auth import manager as auth
from util import notification
import graphene
from controller.attribute import manager


class CreateAttribute(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        attribute_name = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, attribute_name: str):
        auth.check_is_demo(info)
        auth.check_project_access(info, project_id)
        manager.create_attribute(project_id, attribute_name)
        return CreateAttribute(ok=True)


class UpdateAttribute(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        attribute_id = graphene.ID(required=True)
        data_type = graphene.String()
        is_primary_key = graphene.Boolean()

    ok = graphene.Boolean()

    def mutate(
        self,
        info,
        project_id: str,
        attribute_id: str,
        data_type: str,
        is_primary_key: bool,
    ):
        auth.check_is_demo(info)
        auth.check_project_access(info, project_id)
        manager.update_attribute(project_id, attribute_id, data_type, is_primary_key)
        notification.send_organization_update(project_id, f"attributes_updated")
        return UpdateAttribute(ok=True)


class DeleteAttribute(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        attribute_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, attribute_id: str):
        auth.check_is_demo(info)
        auth.check_project_access(info, project_id)
        manager.delete_attribute(project_id, attribute_id)
        return DeleteAttribute(ok=True)


class AddRunningId(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        attribute_name = graphene.ID(required=False)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, attribute_name: str = "running_id"):
        auth.check_is_demo(info)
        auth.check_project_access(info, project_id)
        user = auth.get_user_by_info(info)
        manager.add_running_id(str(user.id), project_id, attribute_name)
        return AddRunningId(ok=True)


class AttributeMutation(graphene.ObjectType):
    create_attribute = CreateAttribute.Field()
    delete_attribute = DeleteAttribute.Field()
    update_attribute = UpdateAttribute.Field()
    add_running_id = AddRunningId.Field()
