from typing import Any, Dict
import graphene

from controller.auth import manager as auth
from controller.misc import config_service
from controller.organization import manager as organization_manager
from controller.user import manager as user_manager
from graphql_api.types import Organization
from submodules.model import events
from util import doc_ock


class AddUserToOrganization(graphene.Mutation):
    class Arguments:
        organization_name = graphene.String()
        user_mail = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, organization_name: str, user_mail: str):
        auth.check_demo_access(info)
        if config_service.get_config_value("is_managed"):
            auth.check_admin_access(info)
        else:
            if not organization_manager.can_create_local(False):
                auth.check_admin_access(info)
        user = auth.get_user_by_email(user_mail)
        user_manager.update_organization_of_user(organization_name, user_mail)
        doc_ock.register_user(user)
        doc_ock.post_event(str(user.id), events.SignUp())
        return AddUserToOrganization(ok=True)


class ChangeUserRole(graphene.Mutation):
    class Arguments:
        user_id = graphene.ID()
        role = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, user_id: str, role: str):
        auth.check_demo_access(info)
        auth.check_admin_access(info)

        user_manager.update_user_role(user_id, role)
        return ChangeUserRole(ok=True)


class ChangeUserLanguageDisplay(graphene.Mutation):
    class Arguments:
        user_id = graphene.ID()
        language_display = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, user_id: str, language_display: str):
        auth.check_demo_access(info)
        auth.check_admin_access(info)

        user_manager.update_user_language_display(user_id, language_display)
        return ChangeUserLanguageDisplay(ok=True)


class RemoveUserFromOrganization(graphene.Mutation):
    class Arguments:
        user_mail = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, user_mail: str):
        auth.check_demo_access(info)
        auth.check_admin_access(info)
        user_manager.remove_organization_from_user(user_mail)
        return RemoveUserFromOrganization(ok=True)


class CreateOrganization(graphene.Mutation):
    class Arguments:
        name = graphene.String()

    organization = graphene.Field(lambda: Organization)

    def mutate(self, info, name: str):
        if config_service.get_config_value("is_managed"):
            auth.check_admin_access(info)
        else:
            if not organization_manager.can_create_local():
                auth.check_admin_access(info)
        organization = organization_manager.create_organization(name)
        return CreateOrganization(organization=organization)


class DeleteOrganization(graphene.Mutation):
    class Arguments:
        name = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, name: str):
        auth.check_demo_access(info)
        auth.check_admin_access(info)
        organization_manager.delete_organization(name)
        return DeleteOrganization(ok=True)


class ChangeOrganization(graphene.Mutation):
    class Arguments:
        org_id = graphene.ID()
        changes = graphene.JSONString()

    ok = graphene.Boolean()

    def mutate(self, info, org_id: str, changes: Dict[str, Any]):
        auth.check_demo_access(info)
        if config_service.get_config_value("is_managed"):
            auth.check_admin_access(info)
        organization_manager.change_organization(org_id, changes)
        return DeleteOrganization(ok=True)


class OrganizationMutation(graphene.ObjectType):
    add_user_to_organization = AddUserToOrganization.Field()
    remove_user_from_organization = RemoveUserFromOrganization.Field()
    change_user_role = ChangeUserRole.Field()
    change_user_language_display = ChangeUserLanguageDisplay.Field()
    create_organization = CreateOrganization.Field()
    delete_organization = DeleteOrganization.Field()
    change_organization = ChangeOrganization.Field()
