from typing import Any, Dict, Optional

from controller.auth import manager as auth
from util import notification
import graphene
from controller.comment import manager


class CreateComment(graphene.Mutation):
    class Arguments:
        comment = graphene.String(required=True)
        xftype = graphene.String(required=True)
        xfkey = graphene.String(required=True)
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
        manager.create_comment(xfkey, xftype, comment, user_id, project_id, is_private)
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
        manager.update_comment(comment_id, user, changes)
        return UpdateComment(ok=True)


class DeleteComment(graphene.Mutation):
    class Arguments:
        link_id = graphene.ID(required=True)
        project_id = graphene.ID(required=False)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, attribute_id: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.delete_attribute(project_id, attribute_id)
        return DeleteComment(ok=True)


class CommentMutation(graphene.ObjectType):
    create_comment = CreateComment.Field()
    delete_comment = DeleteComment.Field()
    update_comment = UpdateComment.Field()
