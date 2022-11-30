import graphene

from controller.auth import manager as auth
from controller.personal_access_token import manager as token_manager
from graphql_api.types import PersonalAccessToken


class PersonalAccessTokenQuery(graphene.ObjectType):

    personal_access_token = graphene.Field(
        PersonalAccessToken,
        project_id=graphene.ID(required=True),
        name=graphene.String(required=True),
    )

    all_personal_access_tokens = graphene.Field(
        graphene.List(PersonalAccessToken), project_id=graphene.ID(required=True)
    )

    def resolve_personal_access_token(
        self, info, project_id: str, name: str
    ) -> PersonalAccessToken:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        auth.check_admin_access(info)
        user_id = auth.get_user_id_by_info(info)
        return token_manager.get_personal_access_token(project_id, user_id, name)

    def resolve_all_personal_access_tokens(
        self, info, project_id: str
    ) -> PersonalAccessToken:
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        auth.check_admin_access(info)
        return token_manager.get_all_personal_access_tokens(project_id)
