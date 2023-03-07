from starlette.endpoints import HTTPEndpoint
from starlette.responses import PlainTextResponse
from submodules.model.business_objects import general


class Healthcheck(HTTPEndpoint):
    def get(self, request) -> PlainTextResponse:
        error_message = ""

        if not __test_database_connection():
            error_message += " database_conncetion "

        text_response = error_message if error_message else "OK"
        return PlainTextResponse(text_response)


def __test_database_connection() -> bool:
    try:
        general.execute("SELECT 1")
        return True
    except Exception:
        return False
