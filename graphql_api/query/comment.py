from typing import Any, Dict, List, Optional, Union

import graphene

from controller.auth import manager as auth
from controller.comment import manager
from submodules.model.enums import CommentCategory


class CommentQuery(graphene.ObjectType):
    has_comments = graphene.Field(
        graphene.JSONString,
        xftype=graphene.String(required=True),
        xfkey=graphene.ID(required=False),
        project_id=graphene.ID(required=False),
        group_by_xfkey=graphene.Boolean(required=False),
    )
    get_comments = graphene.Field(
        graphene.JSONString,
        xftype=graphene.String(required=True),
        xfkey=graphene.ID(required=False),
        project_id=graphene.ID(required=False),
    )

    get_all_comments = graphene.Field(
        graphene.JSONString, requested=graphene.JSONString(required=True)
    )

    # returns a set like list of unique keys that have comments for a given xftype
    get_unique_comments_keys_for = graphene.Field(
        graphene.List(graphene.ID),
        xftype=graphene.String(required=True),
        project_id=graphene.ID(required=False),
    )

    def resolve_has_comments(
        self,
        info,
        xftype: str,
        xfkey: Optional[str] = None,
        project_id: Optional[str] = None,
        group_by_xfkey: bool = False,
    ) -> Union[bool, Dict[str, bool]]:
        auth.check_demo_access(info)
        if project_id:
            auth.check_project_access(info, project_id)
        else:
            auth.check_admin_access(info)
        return manager.has_comments(xftype, xfkey, project_id, group_by_xfkey)

    def resolve_get_comments(
        self,
        info,
        xftype: str,
        xfkey: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> str:
        auth.check_demo_access(info)
        if project_id:
            auth.check_project_access(info, project_id)
        else:
            auth.check_admin_access(info)
        user_id = str(auth.get_user_by_info(info).id)
        return manager.get_comments(xftype, user_id, xfkey, project_id)

    def resolve_get_all_comments(self, info, requested: Dict[str, Any]) -> str:
        auth.check_demo_access(info)
        user_id = str(auth.get_user_by_info(info).id)

        to_return = {}
        for key in requested:
            project_id = requested[key].get("pId")
            if project_id:
                auth.check_project_access(info, project_id)
            else:
                auth.check_admin_access(info)
            comment_id = requested[key].get("commentId")
            if comment_id:
                data = manager.get_comment(
                    requested[key]["xftype"], user_id, comment_id
                )
            else:
                data = manager.get_comments(
                    requested[key]["xftype"],
                    user_id,
                    requested[key].get("xfkey"),
                    project_id,
                )
            add_info = None
            if requested[key].get("includeAddInfo"):
                add_info = manager.get_add_info(
                    requested[key]["xftype"], project_id, requested[key].get("xfkey")
                )
            to_return[key] = {
                "data": data,
                "add_info": add_info,
            }
        return to_return

    def resolve_get_unique_comments_keys_for(
        self, info, xftype: str, project_id: Optional[str] = None
    ) -> List[str]:
        auth.check_demo_access(info)
        if xftype in [CommentCategory.ORGANIZATION.value, CommentCategory.USER.value]:
            auth.check_admin_access(info)
        return manager.get_unique_comments_keys_for(xftype, project_id)
