import graphene

from controller.auth import manager as auth
from graphql_api.types import InformationSourcePayload
from controller.payload import manager


class PayloadQuery(graphene.ObjectType):

    payload_by_payload_id = graphene.Field(
        InformationSourcePayload,
        payload_id=graphene.ID(required=True),
        project_id=graphene.ID(required=True),
    )

    def resolve_payload_by_payload_id(
        self, info, payload_id: str, project_id: str
    ) -> InformationSourcePayload:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return manager.get_payload(project_id, payload_id)
