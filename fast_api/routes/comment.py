import json
from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse
from controller.comment import manager
from controller.auth import manager as auth_manager
from fast_api.models import CreateCommentBody, DeleteCommentBody
from fast_api.routes.client_response import pack_json_result
from submodules.model.enums import CommentCategory
from util import notification


router = APIRouter()


@router.post("/all-comments")
async def get_all_comments(request: Request):
    body = await request.body()

    try:
        requested = json.loads(body)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"message": "Invalid JSON"},
        )

    user_id = str(auth_manager.get_user_by_info(request.state.info).id)

    to_return = {}
    for key in requested:
        project_id = requested[key].get("pId")
        if project_id:
            auth_manager.check_project_access(request.state.info, project_id)
        else:
            auth_manager.check_admin_access(request.state.info)
        comment_id = requested[key].get("commentId")
        if comment_id:
            data = manager.get_comment(requested[key]["xftype"], user_id, comment_id)
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
