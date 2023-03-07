from starlette.endpoints import HTTPEndpoint
from starlette.responses import PlainTextResponse
from submodules.model.business_objects import general


class Healthcheck(HTTPEndpoint):
    def get(self, request) -> PlainTextResponse:
        return PlainTextResponse("OK")


class DatabaseHealthcheck(HTTPEndpoint):
    def get(self, request) -> PlainTextResponse:
        response = "OK"

        if not __test_database_connection():
            response = "FAILED"

        return PlainTextResponse(response)


def __test_database_connection() -> bool:
    try:
        general.execute("SELECT 1")
        return True
    except Exception:
        return False
