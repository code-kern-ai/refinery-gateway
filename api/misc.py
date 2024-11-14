from starlette.endpoints import HTTPEndpoint
from starlette.responses import JSONResponse
from fastapi import Request

from config_handler import (
    full_config_json,
)


class FullConfigRest(HTTPEndpoint):
    def get(self, request: Request) -> JSONResponse:
        return full_config_json()
