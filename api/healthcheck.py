from starlette.endpoints import HTTPEndpoint
from starlette.responses import PlainTextResponse


class Healthcheck(HTTPEndpoint):
    def get(self, request) -> PlainTextResponse:
        return PlainTextResponse("OK")
