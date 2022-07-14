from controller.auth import manager as auth
from controller.knowledge_term import manager
from controller.knowledge_base import manager as base_manager
from controller.auth.manager import get_user_by_info
from util import notification as prj_notification
import graphene


class CreateKnowledgeTerm(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        knowledge_base_id = graphene.ID(required=True)
        value = graphene.String()
        comment = graphene.String()

    ok = graphene.Boolean()

    def mutate(
        self, info, project_id: str, knowledge_base_id: str, value: str, comment: str
    ):
        auth.check_project_access(info, project_id)
        user = get_user_by_info(info)
        manager.create_term(user.id, project_id, knowledge_base_id, value, comment)
        prj_notification.send_organization_update(
            str(project_id), f"knowledge_base_term_updated:{str(knowledge_base_id)}"
        )
        return CreateKnowledgeTerm(ok=True)


class PasteKnowledgeTerms(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        knowledge_base_id = graphene.ID(required=True)
        values = graphene.String(required=True)
        split = graphene.String(required=False)
        delete = graphene.Boolean(required=False)

    ok = graphene.Boolean()

    def mutate(
        self,
        info,
        project_id: str,
        knowledge_base_id: str,
        values: str,
        split: str = "\n",
        delete: bool = False,
    ):
        auth.check_project_access(info, project_id)
        manager.paste_knowledge_terms(
            project_id, knowledge_base_id, values, split, delete
        )
        prj_notification.send_organization_update(
            str(project_id), f"knowledge_base_term_updated:{str(knowledge_base_id)}"
        )
        return CreateKnowledgeTerm(ok=True)


class UpdateKnowledgeTerm(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        term_id = graphene.ID(required=True)
        value = graphene.String()
        comment = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, term_id: str, value: str, comment: str):
        auth.check_project_access(info, project_id)
        base = base_manager.get_knowledge_base_by_term(project_id, term_id)
        user = get_user_by_info(info)
        manager.update_term(project_id, base.id, user.id, term_id, value, comment)
        prj_notification.send_organization_update(
            str(project_id), f"knowledge_base_term_updated:{str(base.id)}"
        )
        return UpdateKnowledgeTerm(ok=True)


class DeleteKnowledgeTerm(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        term_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, term_id: str):
        auth.check_project_access(info, project_id)
        base = base_manager.get_knowledge_base_by_term(project_id, term_id)
        manager.delete_term(project_id, term_id)
        prj_notification.send_organization_update(
            project_id, f"knowledge_base_term_updated:{str(base.id)}"
        )
        return DeleteKnowledgeTerm(ok=True)


class BlacklistTerm(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        term_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, term_id: str):
        auth.check_project_access(info, project_id)
        manager.blacklist_term(term_id)
        return BlacklistTerm(ok=True)


class KnowledgeTermMutation(graphene.ObjectType):
    add_term_to_knowledge_base = CreateKnowledgeTerm.Field()
    update_term = UpdateKnowledgeTerm.Field()
    delete_term = DeleteKnowledgeTerm.Field()
    blacklist_term = BlacklistTerm.Field()
    paste_knowledge_terms = PasteKnowledgeTerms.Field()
