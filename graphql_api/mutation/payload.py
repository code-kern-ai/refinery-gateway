import graphene
from controller.auth import manager as auth
from controller.auth.manager import get_user_by_info
from controller.payload import manager
from graphql_api.types import InformationSourcePayload


class CreatePayload(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID()
        information_source_id = graphene.ID()

    payload = graphene.Field(InformationSourcePayload)

    def mutate(self, info, project_id: str, information_source_id: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user = get_user_by_info(info)
        payload = manager.create_payload(project_id, information_source_id, user.id)
        return CreatePayload(payload)


class PayloadMutation(graphene.ObjectType):
    create_payload = CreatePayload.Field()
