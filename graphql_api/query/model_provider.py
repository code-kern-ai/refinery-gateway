from typing import List, Optional, Dict

from graphql_api import types
from controller.auth import manager as auth_manager
import graphene

from controller.model_provider import manager, connector
from graphql_api.types import ModelProviderInfoResult


class ModelProviderQuery(graphene.ObjectType):

    model_provider_info = graphene.Field(
        ModelProviderInfoResult
    )

    def resolve_model_provider_info(
        self,
        info
    ) -> List[ModelProviderInfoResult]:
        return connector.get_model_provider_info()
