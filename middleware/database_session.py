import logging
from starlette.middleware.base import BaseHTTPMiddleware

from submodules.model.business_objects import general

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class DatabaseSessionHandler(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request, call_next):

        session_token = general.get_ctx_token()

        request.state.session_token = session_token
        try:
            response = await call_next(request)
        finally:
            general.remove_and_refresh_session(session_token)

        return response
