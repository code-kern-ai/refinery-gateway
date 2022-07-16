from typing import List

from controller.auth import manager as auth
from graphql_api import types
from controller.knowledge_term import manager
import graphene

from graphql_api.types import Term


class KnowledgeTermQuery(graphene.ObjectType):

    terms_by_knowledge_base_id = graphene.Field(
        graphene.List(Term),
        project_id=graphene.ID(required=True),
        knowledge_base_id=graphene.ID(required=True),
    )

    def resolve_terms_by_knowledge_base_id(
        self, info, project_id: str, knowledge_base_id: str
    ) -> List[Term]:
        auth.check_project_access(info, project_id)
        return manager.get_terms_by_knowledge_base(project_id, knowledge_base_id)
