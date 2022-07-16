from typing import Optional

from controller.auth import manager as auth
from controller.tokenization import manager
from controller.auth.manager import get_user_by_info
import graphene


class TokenizeRecord(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        record_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, record_id: str):
        auth.check_project_access(info, project_id)
        manager.start_record_tokenization(project_id, record_id)
        return TokenizeRecord(ok=True)


class TokenizeProject(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str):
        auth.check_project_access(info, project_id)
        user = get_user_by_info(info)
        manager.request_tokenize_project(project_id, user.id)
        return TokenizeRecord(ok=True)


class CreateRecordAttributeTokenStatistics(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID()
        attribute_id = graphene.ID()

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, attribute_id: Optional[str] = None):
        auth.check_project_access(info, project_id)
        user = get_user_by_info(info)
        manager.create_rats_entries(project_id, user.id, attribute_id)
        return CreateRecordAttributeTokenStatistics(ok=True)


class TokenizationMutation(graphene.ObjectType):
    create_attribute_token_statistics = CreateRecordAttributeTokenStatistics.Field()
    tokenize_project = TokenizeProject.Field()
    tokenize_record = TokenizeRecord.Field()
