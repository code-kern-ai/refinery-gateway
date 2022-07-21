import logging
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

from submodules.model.session import request_id_ctx_var
from submodules.model.business_objects import general

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class DatabaseSessionHandler(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())
        ctx_token = request_id_ctx_var.set(request_id)
        response = await call_next(request)
        general.remove_session()
        request_id_ctx_var.reset(ctx_token)
        return response
