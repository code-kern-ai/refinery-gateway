from starlette.endpoints import HTTPEndpoint
from starlette.responses import PlainTextResponse
from submodules.model.business_objects import general
from starlette import status


class Healthcheck(HTTPEndpoint):
    def get(self, request) -> PlainTextResponse:
        text = ""
        status_code = status.HTTP_200_OK
        database_test = general.test_database_connection()
        if not database_test.get("success"):
            error_name = database_test.get("error")
            text += f"database_error:{error_name}:"
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if not text:
            text = "OK"
        return PlainTextResponse(text, status_code=status_code)
