import graphene
from typing import List
from graphql_api.types import ModelProviderInfoResult
from controller.auth import manager as auth
from controller.misc import manager as misc
from controller.model_provider import manager


class ModelProviderQuery(graphene.ObjectType):

    model_provider_info = graphene.List(ModelProviderInfoResult)

    def resolve_model_provider_info(self, info) -> List[ModelProviderInfoResult]:
        auth.check_demo_access(info)
        if not misc.check_is_managed():
            print("Not allowed in open source version.")
            return []
        return manager.get_model_provider_info()
