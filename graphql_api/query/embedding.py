from typing import List

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
        project_id=graphene.ID(required=True),
    )

    language_models = graphene.Field(graphene.List(LanguageModel))

    project_tokenization = graphene.Field(
        RecordTokenizationTask, project_id=graphene.ID(required=True)
    )

    def resolve_recommended_encoders(self, info, project_id: str) -> List[Encoder]:
        auth.check_is_demo(info)
        auth.check_project_access(info, project_id)
        return manager.get_recommended_encoders()

    def resolve_language_models(self, info) -> List[LanguageModel]:
        auth.check_is_demo(info)
        return spacy_util.get_language_models()

    def resolve_project_tokenization(
        self, info, project_id: str
    ) -> RecordTokenizationTask:
        auth.check_is_demo(info)
        auth.check_project_access(info, project_id)
        return tokenization.get_record_tokenization_task(project_id)
