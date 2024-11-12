from starlette.endpoints import HTTPEndpoint
from starlette.responses import JSONResponse
from starlette import status
from fastapi import Request

from config_handler import (
    base_config_json,
    full_config_json,
    get_config_value,
)


class IsManagedRest(HTTPEndpoint):
    def get(self, request) -> JSONResponse:
        is_managed = get_config_value("is_managed")
        return JSONResponse(is_managed, status_code=status.HTTP_200_OK)


class IsDemoRest(HTTPEndpoint):
    def get(self, request) -> JSONResponse:
        is_managed = get_config_value("is_demo")
        return JSONResponse(is_managed, status_code=status.HTTP_200_OK)


class FullConfigRest(HTTPEndpoint):
    def get(self, request: Request) -> JSONResponse:
        return full_config_json()


class BaseConfigRest(HTTPEndpoint):
    def get(self, request: Request) -> JSONResponse:
        return base_config_json()
