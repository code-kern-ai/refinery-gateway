from typing import List

from controller.auth import manager as auth_manager
from controller.organization import manager
from graphql_api.types import Organization, User, UserCountsWrapper
import graphene
from graphene_sqlalchemy.fields import SQLAlchemyConnectionField


class OrganizationQuery(graphene.ObjectType):
    user_info = graphene.Field(User)
    all_users = graphene.List(
        User,
        user_role=graphene.String(required=False),
    )
    all_users_with_record_count = graphene.List(
        UserCountsWrapper, project_id=graphene.ID()
    )
    user_organization = graphene.Field(Organization)
    all_organizations = SQLAlchemyConnectionField(Organization.connection)

    overview_stats = graphene.Field(
        graphene.JSONString,
    )

    can_create_local_org = graphene.Field(graphene.Boolean)

    def resolve_user_info(self, info) -> User:
        auth_manager.check_demo_access(info)
        return auth_manager.get_user_by_info(info)

    def resolve_all_users(self, info, user_role: str = None) -> List[User]:
        auth_manager.check_demo_access(info)
        organization_id = str(auth_manager.get_user_by_info(info).organization.id)
        return manager.get_all_users(organization_id, user_role)

    def resolve_all_users_with_record_count(
        self, info, project_id: str
    ) -> List[UserCountsWrapper]:
        auth_manager.check_demo_access(info)
        organization_id = str(auth_manager.get_user_by_info(info).organization.id)
        return manager.get_all_users_with_record_count(organization_id, project_id)

    def resolve_user_organization(self, info) -> Organization:
        auth_manager.check_demo_access(info)
        return auth_manager.get_user_by_info(info).organization

    def resolve_all_organizations(self, info, sort) -> List[Organization]:
        auth_manager.check_demo_access(info)
        auth_manager.check_admin_access(info)
        return manager.get_all_organizations()

    def resolve_overview_stats(
        self,
        info,
    ) -> str:
        auth_manager.check_demo_access(info)
        org_id = str(auth_manager.get_user_by_info(info).organization_id)
        return manager.get_overview_stats(org_id)

    def resolve_can_create_local_org(self, info) -> bool:
        auth_manager.check_demo_access(info)
        return manager.can_create_local()
