import graphene
from graphql import GraphQLError
from controller.auth import manager as auth
from controller.misc import manager as misc
from controller.model_provider import manager


class ModelProviderDownloadModel(graphene.Mutation):
    class Arguments:
        model_name = graphene.String(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, model_name: str):
        auth.check_demo_access(info)
        if misc.check_is_managed:
            if not auth.check_is_single_organization():
                auth.check_admin_access(info)
        else:
            raise GraphQLError("Not allowed in open source version.")
        manager.model_provider_download_model(model_name)
        return ModelProviderDownloadModel(ok=True)


class ModelProviderDeleteModel(graphene.Mutation):
    class Arguments:
        model_name = graphene.String(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, model_name: str):
        auth.check_demo_access(info)
        if misc.check_is_managed:
            if not auth.check_is_single_organization():
                auth.check_admin_access(info)
        else:
            raise GraphQLError("Not allowed in open source version.")
        manager.model_provider_delete_model(model_name)
        return ModelProviderDownloadModel(ok=True)


class ModelProviderMutation(graphene.ObjectType):
    model_provider_download_model = ModelProviderDownloadModel.Field()
    model_provider_delete_model = ModelProviderDeleteModel.Field()
