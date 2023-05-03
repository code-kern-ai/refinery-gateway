from typing import Optional

from controller.auth import manager as auth
from controller.tokenization import manager
from controller.auth.manager import get_user_by_info
import graphene
from controller.task_queue import manager as task_queue_manager
from submodules.model.enums import TaskType, RecordTokenizationScope


class TokenizeRecord(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        record_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, record_id: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.start_record_tokenization(project_id, record_id)
        return TokenizeRecord(ok=True)


class TokenizeProject(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user = get_user_by_info(info)
        task_queue_manager.add_task(
            project_id,
            TaskType.TOKENIZATION,
            str(user.id),
            {
                "scope": RecordTokenizationScope.PROJECT.value,
                "include_rats": True,
                "only_uploaded_attributes": False,
            },
        )
        return TokenizeRecord(ok=True)


class CreateRecordAttributeTokenStatistics(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID()
        attribute_id = graphene.ID()

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, attribute_id: Optional[str] = None):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user = get_user_by_info(info)
        manager.create_rats_entries(project_id, user.id, attribute_id)
        return CreateRecordAttributeTokenStatistics(ok=True)


class TokenizationMutation(graphene.ObjectType):
    create_attribute_token_statistics = CreateRecordAttributeTokenStatistics.Field()
    tokenize_project = TokenizeProject.Field()
    tokenize_record = TokenizeRecord.Field()
