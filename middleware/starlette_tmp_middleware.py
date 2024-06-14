import logging
from starlette.middleware.base import BaseHTTPMiddleware
from submodules.model.business_objects import general
import traceback
from fast_api.routes.client_response import GENERIC_FAILURE_RESPONSE

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class DatabaseSessionHandler(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request, call_next):
        if request.url.path.startswith("/api"):
            # fast api middleware handles these
            return await call_next(request)

        session_token = general.get_ctx_token()
        try:
            response = await call_next(request)
            # finally is still called even if returned response
            return response
        except Exception:
            print(traceback.format_exc(), flush=True)
            return GENERIC_FAILURE_RESPONSE
        finally:
            general.remove_and_refresh_session(session_token)
