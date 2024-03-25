import json
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from controller.auth import manager as auth_manager
from controller.comment import manager as comment_manager
from fast_api.routes.client_response import pack_json_result


router = APIRouter()


@router.post("/{project_id}/record-comments")
async def get_record_comments(request: Request, project_id: str):
    body = await request.body()

    try:
        record_ids = json.loads(body)["recordIds"]
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"message": "Invalid JSON"},
        )

    user_id = auth_manager.get_user_id_by_info(request.state.info)
    data = comment_manager.get_record_comments(project_id, user_id, record_ids)
    return pack_json_result(
        {"data": {"getRecordComments": data}}, wrap_for_frontend=False
    )
