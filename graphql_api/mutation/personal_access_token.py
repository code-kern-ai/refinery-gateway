from controller.auth import manager as auth
import graphene


class CreatePersonalAccessToken(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        name = graphene.String(required=True)
        scope = graphene.String(required=True)
        expires_at = graphene.String(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, name: str, scope: str, expires_at: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        print("Hello from PAT creation", project_id, name, scope, expires_at)
        return CreatePersonalAccessToken(ok=True)


class PersonalAccessTokenMutations(graphene.ObjectType):
    create_personal_access_token = CreatePersonalAccessToken.Field()
