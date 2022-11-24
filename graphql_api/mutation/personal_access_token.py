from controller.auth import manager as auth
from controller.personal_access_token import manager as token_manager
import graphene


class CreatePersonalAccessToken(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        name = graphene.String(required=True)
        scope = graphene.String(required=True)
        expires_at = graphene.String(required=True)

    token = graphene.String()

    def mutate(self, info, project_id: str, name: str, scope: str, expires_at: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user_id = auth.get_user_id_by_info(info)
        token = token_manager.create_personal_access_token(
            project_id=project_id,
            user_id=user_id,
            name=name,
            scope=scope,
            expires_at=expires_at,
        )
        return CreatePersonalAccessToken(token=token)


class DeletePersonalAccessToken(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        token_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, token_id: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user_id = auth.get_user_id_by_info(info)
        token_manager.delete_personal_access_token(
            project_id=project_id, user_id=user_id, token_id=token_id
        )
        return DeletePersonalAccessToken(ok=True)


class PersonalAccessTokenMutations(graphene.ObjectType):
    create_personal_access_token = CreatePersonalAccessToken.Field()
    delete_personal_access_token = DeletePersonalAccessToken.Field()
