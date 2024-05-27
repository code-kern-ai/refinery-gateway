from fastapi import APIRouter, Body, Request, Depends
from controller.comment import manager
from controller.auth import manager as auth_manager
from fast_api.models import (
    AllCommentsBody,
    CreateCommentBody,
    DeleteCommentBody,
    UpdateCommentBody,
)
from fast_api.routes.client_response import pack_json_result
from submodules.model.enums import CommentCategory
from util import notification
from middleware.log_storage import extend_state_get_like


router = APIRouter()


@router.post(
    "/all-comments",
    dependencies=[Depends(extend_state_get_like)],
)
def get_all_comments(request: Request, commentsBody: AllCommentsBody = Body(...)):
    user_id = str(auth_manager.get_user_by_info(request.state.info).id)
    body = commentsBody.__root__

    to_return = {}
    for key in body:
        xfkey = body[key].get("xfkey")
        xftype = body[key].get("xftype")
        project_id = body[key].get("pId")
        comment_id = body[key].get("commentId")
        includeAddInfo = body[key].get("includeAddInfo")

        if project_id:
            auth_manager.check_project_access(request.state.info, project_id)
        else:
            auth_manager.check_admin_access(request.state.info)

        if comment_id:
            data = manager.get_comment_by_comment_id(user_id, comment_id)
        else:
            data = manager.get_comments(
                xftype,
                user_id,
                xfkey,
                project_id,
            )

        add_info = None
        if includeAddInfo and xftype:
            add_info = manager.get_add_info(xftype, project_id, xfkey)

        to_return[key] = {
            "data": data,
            "add_info": add_info,
        }

    return pack_json_result(
        {"data": {"getAllComments": to_return}}, wrap_for_frontend=False
    )


@router.post("/create-comment")
def create_comment(request: Request, body: CreateCommentBody = Body(...)):
    user_id = str(auth_manager.get_user_by_info(request.state.info).id)

    if body.project_id:
        auth_manager.check_project_access(request.state.info, body.project_id)
    else:
        auth_manager.check_admin_access(request.state.info)

    if body.xftype == CommentCategory.USER.value:
        user_id = body.xfkey

    item = manager.create_comment(
        body.xfkey, body.xftype, body.comment, user_id, body.project_id, body.is_private
    )

    if item and body.project_id:
        notification.send_organization_update(
            body.project_id,
            f"comment_created:{body.project_id}:{body.xftype}:{body.xfkey}:{str(item.id)}",
            True,
        )

    return pack_json_result({"data": {"createComment": {"ok": True}}})


@router.delete("/delete-comment")
def delete_comment(
    request: Request,
    body: DeleteCommentBody = Body(...),
):
    if body.project_id:
        auth_manager.check_project_access(request.state.info, body.project_id)
    else:
        auth_manager.check_admin_access(request.state.info)

    user_id = auth_manager.get_user_id_by_info(request.state.info)
    manager.delete_comment(body.comment_id, user_id)

    if body.project_id:
        # without project_id its a admin dashboard comment -> no websocket integration planned atm
        # global notification since the data is collected globally -> further handling in frontend
        notification.send_organization_update(
            body.project_id,
            f"comment_deleted:{body.project_id}:{body.comment_id}",
            True,
        )

    return pack_json_result({"data": {"deleteComment": {"ok": True}}})


@router.put("/update-comment")
def update_comment(
    request: Request,
    body: UpdateCommentBody = Body(...),
):
    if body.project_id:
        auth_manager.check_project_access(request.state.info, body.project_id)
    else:
        auth_manager.check_admin_access(request.state.info)

    user = auth_manager.get_user_by_info(request.state.info)
    item = manager.update_comment(body.comment_id, user, body.changes)

    if item and body.project_id:
        # without project_id its a admin dashboard comment -> no websocket integration planned atm
        # global notification since the data is collected globally -> further handling in frontend
        notification.send_organization_update(
            body.project_id,
            f"comment_updated:{body.project_id}:{body.comment_id}",
            True,
        )

    return pack_json_result({"data": {"updateComment": {"ok": True}}})


@router.get("/get-unique-comments-keys-for")
def get_unique_comments_keys_for(request: Request, xftype: str):
    if xftype in [CommentCategory.ORGANIZATION.value, CommentCategory.USER.value]:
        auth_manager.check_admin_access(request.state.info)
    return manager.get_unique_comments_keys_for(xftype)
