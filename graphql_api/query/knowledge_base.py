from typing import List

from controller.auth import manager as auth
from controller.knowledge_base import manager
from controller.knowledge_term import manager as term_manager
from graphql_api import types
import graphene

from graphql_api.types import KnowledgeBase, Term


class KnowledgeBaseQuery(graphene.ObjectType):

    knowledge_base_by_knowledge_base_id = graphene.Field(
        KnowledgeBase,
        project_id=graphene.ID(required=True),
        knowledge_base_id=graphene.ID(required=True),
    )

    knowledge_bases_by_project_id = graphene.Field(
        graphene.List(KnowledgeBase),
        project_id=graphene.ID(required=True),
    )

    terms_by_knowledge_base_id = graphene.Field(
        graphene.List(Term),
        project_id=graphene.ID(required=True),
        knowledge_base_id=graphene.ID(required=True),
    )

    def resolve_knowledge_base_by_knowledge_base_id(
        self, info, project_id: str, knowledge_base_id: str
    ) -> KnowledgeBase:
        auth.check_is_demo(info)
        auth.check_project_access(info, project_id)
        return manager.get_knowledge_base(project_id, knowledge_base_id)

    def resolve_knowledge_bases_by_project_id(
        self, info, project_id: str
    ) -> List[KnowledgeBase]:
        auth.check_is_demo(info)
        auth.check_project_access(info, project_id)
        return manager.get_all_knowledge_bases(project_id)

    def resolve_by_knowledge_base_id(
        self, info, project_id: str, knowledge_base_id: str
    ) -> List[Term]:
        auth.check_is_demo(info)
        auth.check_project_access(info, project_id)
        return term_manager.get_terms_by_knowledge_base(project_id, knowledge_base_id)
