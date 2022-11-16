from typing import List, Optional

import graphene

from controller.auth import manager as auth
from graphql_api import types
from graphql_api.types import Encoder, LanguageModel, RecordTokenizationTask
from submodules.model.business_objects import tokenization
from util import spacy_util
from controller.embedding import manager


class EmbeddingQuery(graphene.ObjectType):
    recommended_encoders = graphene.Field(
        graphene.List(Encoder),
        project_id=graphene.ID(required=False),
    )

    language_models = graphene.Field(graphene.List(LanguageModel))

    project_tokenization = graphene.Field(
        RecordTokenizationTask, project_id=graphene.ID(required=True)
    )

    def resolve_recommended_encoders(
        self, info, project_id: Optional[str] = None
    ) -> List[Encoder]:
        auth.check_demo_access(info)
        if project_id:
            auth.check_project_access(info, project_id)
        return manager.get_recommended_encoders()

    def resolve_language_models(self, info) -> List[LanguageModel]:
        auth.check_demo_access(info)
        return spacy_util.get_language_models()

    def resolve_project_tokenization(
        self, info, project_id: str
    ) -> RecordTokenizationTask:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        return tokenization.get_record_tokenization_task(project_id)
