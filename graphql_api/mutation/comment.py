from typing import Any, Dict, Optional

from controller.auth import manager as auth
from util import notification
import graphene
from controller.comment import manager


def send_notification():
    pass


class CreateComment(graphene.Mutation):
    class Arguments:
        comment = graphene.String(required=True)
        xftype = graphene.String(required=True)
        xfkey = graphene.ID(required=True)
        project_id = graphene.ID(required=False)
        is_private = graphene.Boolean(required=False)

    ok = graphene.Boolean()

    def mutate(
        self,
        info,
        comment: str,
        xftype: str,
        xfkey: str,
        project_id: Optional[str] = None,
        is_private: Optional[bool] = False,
    ):
        auth.check_demo_access(info)
        if project_id:
            auth.check_project_access(info, project_id)
        else:
            auth.check_admin_access(info)
        user_id = auth.get_user_id_by_info(info)
        item = manager.create_comment(
            xfkey, xftype, comment, user_id, project_id, is_private
        )
        if item and project_id:
            # without project_id its a admin dashboard comment -> no websocket integration planned atm
            # global notification since the data is collected globally -> further handling in frontend
            notification.send_organization_update(
                project_id,
                f"comment_created:{project_id}:{xftype}:{xfkey}:{str(item.id)}",
                True,
            )
        return CreateComment(ok=True)


class UpdateComment(graphene.Mutation):
    class Arguments:
        comment_id = graphene.ID(required=True)
        changes = graphene.JSONString(required=True)
        project_id = graphene.ID(required=False)

    ok = graphene.Boolean()

    def mutate(
        self,
        info,
        comment_id: str,
        changes: Dict[str, Any],
        project_id: Optional[str] = None,
    ):
        auth.check_demo_access(info)
        if project_id:
            auth.check_project_access(info, project_id)
        else:
            auth.check_admin_access(info)
        user = auth.get_user_by_info(info)
        item = manager.update_comment(comment_id, user, changes)
        if item and project_id:
            # without project_id its a admin dashboard comment -> no websocket integration planned atm
            # global notification since the data is collected globally -> further handling in frontend
            notification.send_organization_update(
                project_id,
                f"comment_updated:{project_id}:{comment_id}:{item.xftype}:{item.xfkey}",
                True,
            )
        return UpdateComment(ok=True)


class DeleteComment(graphene.Mutation):
    class Arguments:
        comment_id = graphene.ID(required=True)
        project_id = graphene.ID(required=False)

    ok = graphene.Boolean()

    def mutate(
        self,
        info,
        comment_id: str,
        project_id: Optional[str] = None,
    ):
        auth.check_demo_access(info)
        if project_id:
            auth.check_project_access(info, project_id)
        else:
            auth.check_admin_access(info)
        user_id = auth.get_user_id_by_info(info)
        manager.delete_comment(comment_id, user_id)
        if project_id:
            # without project_id its a admin dashboard comment -> no websocket integration planned atm
            # global notification since the data is collected globally -> further handling in frontend
            notification.send_organization_update(
                project_id, f"comment_deleted:{project_id}:{comment_id}", True
            )
        return DeleteComment(ok=True)


class CommentMutation(graphene.ObjectType):
    create_comment = CreateComment.Field()
    delete_comment = DeleteComment.Field()
    update_comment = UpdateComment.Field()
