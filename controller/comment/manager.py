from typing import Any, Dict, List, Optional, Union
from controller.auth import kratos
from controller.auth import manager as user_manager
from submodules.model import enums
from submodules.model.models import CommentData, User

from submodules.model.business_objects import comments


def has_comments(
    xftype: str,
    xfkey: Optional[str] = None,
    project_id: Optional[str] = None,
    group_by_xfkey: bool = False,
) -> Union[bool, Dict[str, bool]]:

    try:
        xftype_parsed = enums.CommentCategory[xftype.upper()]
    except KeyError:
        raise ValueError(f"Invalid comment category: {xftype}")

    return comments.has_comments(xftype_parsed, xfkey, project_id, group_by_xfkey)


def get_comments(
    xftype: str,
    user_id: str,
    xfkey: Optional[str] = None,
    project_id: Optional[str] = None,
) -> str:

    try:
        xftype_parsed = enums.CommentCategory[xftype.upper()]
    except KeyError:
        raise ValueError(f"Invalid comment category: {xftype}")

    return comments.get_by_all_by_category(
        xftype_parsed, user_id, xfkey, project_id, True
    )


def get_add_info(
    xftype: str,
    project_id: Optional[str] = None,
) -> str:

    try:
        xftype_parsed = enums.CommentCategory[xftype.upper()]
    except KeyError:
        raise ValueError(f"Invalid comment category: {xftype}")

    values = comments.get_add_info_category(xftype_parsed, project_id)

    if xftype_parsed == enums.CommentCategory.USER:
        values = [
            {"id": r.id, "name": kratos.resolve_user_mail_by_id(r.id)} for r in values
        ]
    return values


def create_comment(
    xfkey: str,
    xftype: str,
    comment: str,
    user_id: str,
    project_id: Optional[str] = None,
    is_private: Optional[bool] = None,
) -> CommentData:
    try:
        xftype = enums.CommentCategory[xftype.upper()].value
    except KeyError:
        raise ValueError(f"Invalid comment type: {xftype}")
    comments.create(
        xfkey,
        xftype,
        comment,
        user_id,
        project_id,
        None,
        None,
        is_private,
        None,
        with_commit=True,
    )


def update_comment(
    comment_id: str,
    user: User,
    changes: Dict[str, Any],
) -> CommentData:
    item = comments.get(comment_id)

    if not item:
        raise ValueError(f"Can't find comment")

    if user.role != enums.UserRoles.ENGINEER.value and user.id != item.created_by:
        raise ValueError(f"Can't update comment")
    comments.change(item, changes, with_commit=True)


def delete_comment(comment_id: str, user_id: str) -> CommentData:
    item = comments.get(comment_id)
    if not item:
        raise ValueError(f"Can't find comment")

    if (
        item.created_by != user_id
        and user_manager.get_user_role_by_id(user_id) != enums.UserRoles.ENGINEER.value
    ):
        raise ValueError(f"Can't delete comment")
    comments.remove(comment_id, with_commit=True)
