import graphene

from submodules.model import enums
from controller.auth import manager as auth
from util.notification import create_notification


class CreateNotification(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        message = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, message: str, project_id: str):

        user = auth.get_user_by_info(info)
        create_notification(
            enums.NotificationType.CUSTOM, user.id, project_id, message,
        )
        return CreateNotification(ok=True)


class NotificationMutation(graphene.ObjectType):
    create_notification = CreateNotification.Field()
