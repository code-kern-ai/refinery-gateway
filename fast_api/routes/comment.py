import json
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from controller.comment import manager
from controller.auth import manager as auth_manager
from fast_api.routes.client_response import pack_json_result


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
