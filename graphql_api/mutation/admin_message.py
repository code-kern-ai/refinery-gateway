from controller.auth import manager as auth
from controller.admin_message import manager
import graphene


class CreateAdminMessage(graphene.Mutation):
    class Arguments:
        text = graphene.String(required=True)
        level = graphene.String(required=True)
        archive_date = graphene.DateTime(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, text: str, level: str, archive_date):
        auth.check_demo_access(info)
        auth.check_admin_access(info)
        user_id = auth.get_user_id_by_info(info)
        manager.create_admin_message(text, level, archive_date, user_id)
        return CreateAdminMessage(ok=True)


class ArchiveAdminMessage(graphene.Mutation):
    class Arguments:
        message_id = graphene.ID(required=True)
        archived_reason = graphene.String(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, message_id: str, archived_reason: str):
        auth.check_demo_access(info)
        auth.check_admin_access(info)
        user_id = auth.get_user_id_by_info(info)
        manager.archive_admin_message(message_id, user_id, archived_reason),
        return ArchiveAdminMessage(ok=True)


class AdminMessageMutation(graphene.ObjectType):
    create_admin_message = CreateAdminMessage.Field()
    archive_admin_message = ArchiveAdminMessage.Field()
