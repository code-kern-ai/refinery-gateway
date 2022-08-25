import graphene
from typing import List
from graphql_api.types import ModelProviderInfoResult
from controller.model_provider import manager


class ModelProviderQuery(graphene.ObjectType):

    model_provider_info = graphene.List(ModelProviderInfoResult)

    def resolve_model_provider_info(self, info) -> List[ModelProviderInfoResult]:
        return manager.get_model_provider_info()
