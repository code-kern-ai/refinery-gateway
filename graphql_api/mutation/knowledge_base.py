from typing import Optional

from controller.auth import manager as auth
from controller.knowledge_base import manager
from graphql_api import types
from controller.auth.manager import get_user_by_info
from graphql_api.types import KnowledgeBase
from util import notification as prj_notification
import graphene


class CreateKnowledgeBase(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)

    knowledge_base = graphene.Field(KnowledgeBase)

    def mutate(self, info, project_id: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        knowledge_base = manager.create_knowledge_base(project_id)
        prj_notification.send_organization_update(
            project_id, f"knowledge_base_created:{str(knowledge_base.id)}"
        )
        return CreateKnowledgeBase(knowledge_base=knowledge_base)


class DeleteKnowledgeBase(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        knowledge_base_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, knowledge_base_id: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.delete_knowledge_base(project_id, knowledge_base_id)
        prj_notification.send_organization_update(
            project_id, f"knowledge_base_deleted:{str(knowledge_base_id)}"
        )
        return DeleteKnowledgeBase(ok=True)


class UpdateKnowledgeBase(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        knowledge_base_id = graphene.ID(required=True)
        name = graphene.String()
        description = graphene.String()

    ok = graphene.Boolean()

    def mutate(
        self,
        info,
        project_id: str,
        knowledge_base_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user = get_user_by_info(info)
        manager.update_knowledge_base(
            project_id, user.id, knowledge_base_id, name, description
        )
        prj_notification.send_organization_update(
            str(project_id), f"knowledge_base_updated:{str(knowledge_base_id)}"
        )
        return UpdateKnowledgeBase(ok=True)


class KnowledgeBaseMutation(graphene.ObjectType):
    create_knowledge_base = CreateKnowledgeBase.Field()
    update_knowledge_base = UpdateKnowledgeBase.Field()
    delete_knowledge_base = DeleteKnowledgeBase.Field()
