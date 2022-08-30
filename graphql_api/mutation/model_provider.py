import graphene
from controller.auth import manager as auth
from controller.misc import manager as misc
from controller.model_provider import manager


class ModelProviderDownloadModel(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        model_name = graphene.String(required=True)
        revision = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, model_name: str, revision: str = None):
        auth.check_demo_access(info)
        if misc.check_is_managed:
            auth.check_admin_access(info)
        manager.model_provider_download_model(project_id, model_name, revision)
        return ModelProviderDownloadModel(ok=True)


class ModelProviderDeleteModel(graphene.Mutation):
    class Arguments:
        model_name = graphene.String(required=True)
        revision = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, model_name: str, revision: str):
        auth.check_demo_access(info)
        if misc.check_is_managed:
            auth.check_admin_access(info)
        manager.model_provider_delete_model(model_name, revision)
        return ModelProviderDownloadModel(ok=True)


class ModelProviderMutation(graphene.ObjectType):
    model_provider_download_model = ModelProviderDownloadModel.Field()
    model_provider_delete_model = ModelProviderDeleteModel.Field()
