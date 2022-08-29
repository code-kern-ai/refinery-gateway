import graphene
from controller.model_provider import manager


class CreateModelProvider(graphene.Mutation):
    class Arguments:
        model_name = graphene.String(required=True)
        revision = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, model_name: str, revision: str = None):
        manager.create_model_provider(model_name, revision)

        return CreateModelProvider(ok=True)


class DeleteModelProvider(graphene.Mutation):
    class Arguments:
        model_name = graphene.String(required=True)
        revision = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, model_name: str, revision: str):
        manager.delete_model_provider(model_name, revision)

        return DeleteModelProvider(ok=True)


class ModelProviderMutation(graphene.ObjectType):
    create_model_provider = CreateModelProvider.Field()
    delete_model_provider = DeleteModelProvider.Field()
