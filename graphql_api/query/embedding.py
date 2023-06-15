from typing import List, Optional

import graphene

from controller.misc import manager as misc
from controller.auth import manager as auth
from graphql_api.types import EmbeddingPlatform, Encoder, LanguageModel, RecordTokenizationTask
from submodules.model import enums
from submodules.model.business_objects import tokenization, task_queue
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

    embedding_platforms = graphene.Field(graphene.List(EmbeddingPlatform))

    def resolve_recommended_encoders(
        self, info, project_id: Optional[str] = None
    ) -> List[Encoder]:
        auth.check_demo_access(info)
        if project_id:
            auth.check_project_access(info, project_id)
        is_managed = misc.check_is_managed()
        return manager.get_recommended_encoders(is_managed)

    def resolve_language_models(self, info) -> List[LanguageModel]:
        auth.check_demo_access(info)
        return spacy_util.get_language_models()

    def resolve_project_tokenization(
        self, info, project_id: str
    ) -> RecordTokenizationTask:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        ##check queued stuff
        waiting_task = task_queue.get_by_tokenization(project_id)
        if waiting_task and not waiting_task.is_active:
            return RecordTokenizationTask(
                id=waiting_task.id,
                started_at=waiting_task.created_at,
                state="QUEUED",
                progress=-1,
            )
        return tokenization.get_record_tokenization_task(project_id)

    def resolve_embedding_platforms(self, info) -> List[EmbeddingPlatform]:
        return [
            {
            "platform": enums.EmbeddingPlatform.HUGGINGFACE.value,
            "terms": None,
            "link": None
            },
            {
            "platform": enums.EmbeddingPlatform.COHERE.value,
            "terms": "Please note that by enabling this third-party API, you are stating that you accept its addition as a sub-processor under the terms of our Data Processing Agreement. Please be aware that the Cohere API policies may conflict with your internal data and privacy policies. For more information please check: @@PLACEHOLDER@@. For questions you can contact us at security@kern.ai.",
            "link": "https://openai.com/policies/api-data-usage-policies"
            }, 
            {
            "platform": enums.EmbeddingPlatform.OPENAI.value,
            "terms": "Please note that by enabling this third-party API, you are stating that you accept its addition as a sub-processor under the terms of our Data Processing Agreement. Please be aware that the OpenAI API policies may conflict with your internal data and privacy policies. For more information please check: @@PLACEHOLDER@@. For questions you can contact us at security@kern.ai.",
            "link": "https://openai.com/policies/api-data-usage-policies"
            },
            {
            "platform": enums.EmbeddingPlatform.PYTHON.value,
            "terms": None,
            "link": None
            },
        ]