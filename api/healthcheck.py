from starlette.endpoints import HTTPEndpoint
from starlette.responses import PlainTextResponse
from submodules.model.business_objects import general


class Healthcheck(HTTPEndpoint):
    def get(self, request) -> PlainTextResponse:
        return PlainTextResponse("OK")


class DatabaseHealthcheck(HTTPEndpoint):
    def get(self, request) -> PlainTextResponse:
        response = "OK" if general.test_database_connection() else "FAILED"
        return PlainTextResponse(response)
