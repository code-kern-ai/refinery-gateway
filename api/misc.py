from controller.misc import config_service
from starlette.endpoints import HTTPEndpoint
from starlette.responses import JSONResponse
from starlette import status


class IsManagedRest(HTTPEndpoint):
    def get(self, request) -> JSONResponse:
        is_managed = config_service.get_config_value("is_managed")
        return JSONResponse(is_managed, status_code=status.HTTP_200_OK)

class IsDemoRest(HTTPEndpoint):
    def get(self, request) -> JSONResponse:
        is_managed = config_service.get_config_value("is_demo")
        return JSONResponse(is_managed, status_code=status.HTTP_200_OK)
