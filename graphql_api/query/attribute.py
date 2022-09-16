import graphene
from typing import List

from controller.auth import manager as auth
from controller.attribute import manager
from submodules.model.enums import NotificationType
from graphql_api.types import Attribute, UserAttributeSampleRecordsResult
from util.notification import create_notification


class AttributeQuery(graphene.ObjectType):

    attribute_by_attribute_id = graphene.Field(
        Attribute,
        project_id=graphene.ID(required=True),
        attribute_id=graphene.ID(required=True),
    )

    attributes_by_project_id = graphene.Field(
        graphene.List(Attribute),
        project_id=graphene.ID(required=True),
    )

    check_composite_key = graphene.Field(
        graphene.Boolean,
        project_id=graphene.ID(required=True),
    )

    calculate_user_attribute_sample_records = graphene.Field(
        UserAttributeSampleRecordsResult,
        project_id=graphene.ID(required=True),
        attribute_id=graphene.ID(required=True),
    )

    def resolve_attribute_by_attribute_id(
        self, info, project_id: str, attribute_id: str
    ) -> Attribute:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return manager.get_attribute(project_id, attribute_id)

    def resolve_attributes_by_project_id(
        self, info, project_id: str
    ) -> List[Attribute]:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return manager.get_all_attributes(project_id)

    def resolve_check_composite_key(self, info, project_id: str) -> bool:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user = auth.get_user_by_info(info)
        is_valid = manager.check_composite_key(project_id)
        if not is_valid:
            create_notification(
                NotificationType.INVALID_PRIMARY_KEY,
                user.id,
                project_id,
            )
        return is_valid

    def resolve_calculate_user_attribute_sample_records(
        self, info, project_id: str, attribute_id: str
    ) -> UserAttributeSampleRecordsResult:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return UserAttributeSampleRecordsResult(
            *manager.calculate_user_attribute_sample_records(project_id, attribute_id)
        )
