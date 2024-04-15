import json
from typing import Any, Optional
from fastapi.responses import JSONResponse, Response
from fastapi import status
from sqlalchemy.engine.row import Row
from submodules.model.models import Base
from submodules.model.util import sql_alchemy_to_dict, to_frontend_obj, is_list_like
from pydantic import BaseModel


def pack_json_result(
    content: Optional[Any] = None,
    status_code: Optional[int] = None,
    wrap_for_frontend: bool = True,
):
    if content is None:
        if not status_code:
            status_code = status.HTTP_204_NO_CONTENT
        return Response(
            status_code=status_code,
        )
    else:
        if wrap_for_frontend:
            content = wrap_content_for_frontend(content)
        if not status_code:
            status_code = status.HTTP_200_OK
        return JSONResponse(
            status_code=status_code,
            content=content,
        )


def wrap_content_for_frontend(content: Any):
    if not content:
        return content
    if is_list_like(content):
        return [wrap_content_for_frontend(item) for item in content]
    else:
        if isinstance(content, BaseModel):
            return to_json(content)
        elif isinstance(content, Row) or isinstance(content, Base):
            return sql_alchemy_to_dict(content, for_frontend=True)
        else:
            return to_frontend_obj(content)


SILENT_SUCCESS_RESPONSE = JSONResponse(
    status_code=status.HTTP_200_OK,
    content={"message": "Success"},
)


def get_silent_success() -> JSONResponse:
    return SILENT_SUCCESS_RESPONSE


def to_json(obj: BaseModel):
    return json.loads(obj.json())
