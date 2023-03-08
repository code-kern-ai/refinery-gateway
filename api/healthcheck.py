from starlette.endpoints import HTTPEndpoint
from starlette.responses import PlainTextResponse
from submodules.model.business_objects import general


class Healthcheck(HTTPEndpoint):
    def get(self, request) -> PlainTextResponse:
        headers = {"APP": "OK"}
        database_test = general.test_database_connection()
        if not database_test.get("success"):
            headers["DATABASE"] = database_test.get("error")
        return PlainTextResponse("OK", headers=headers)
