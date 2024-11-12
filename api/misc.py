from starlette.endpoints import HTTPEndpoint
from starlette.responses import JSONResponse
from starlette import status
from fastapi import Request, responses
import json

from config_handler import (
    base_config_json,
    change_json,
    full_config_json,
    get_config_value,
)

from fast_api.models import (
    ChangeRequest,
)


class IsManagedRest(HTTPEndpoint):
    def get(self, request) -> JSONResponse:
        is_managed = get_config_value("is_managed")
        return JSONResponse(is_managed, status_code=status.HTTP_200_OK)


class IsDemoRest(HTTPEndpoint):
    def get(self, request) -> JSONResponse:
        is_managed = get_config_value("is_demo")
        return JSONResponse(is_managed, status_code=status.HTTP_200_OK)


class ChangeConfigRest(HTTPEndpoint):
    async def post(self, request: Request) -> JSONResponse:
        try:
            data = await request.json()
            change_request = ChangeRequest(**data)
            config_data = json.loads(change_request.dict_string)
            return change_json(config_data)
        except Exception as e:
            return responses.PlainTextResponse(
                f"Error: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FullConfigRest(HTTPEndpoint):
    def get(self, request: Request) -> JSONResponse:
        return full_config_json()


class BaseConfigRest(HTTPEndpoint):
    def get(self, request: Request) -> JSONResponse:
        return base_config_json()
