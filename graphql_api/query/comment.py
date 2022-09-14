from typing import Dict, List, Optional, Union

import graphene

from controller.auth import manager as auth
from graphql_api.types import DataSlice
from controller.comment import manager


class CommentQuery(graphene.ObjectType):

    has_comments = graphene.Field(
        graphene.JSONString,
        xftype=graphene.String(required=True),
        xfkey=graphene.ID(required=False),
        project_id=graphene.ID(required=False),
        group_by_xfkey=graphene.Boolean(required=False),
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
