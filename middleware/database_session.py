import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from graphql import GraphQLError
from starlette.middleware.base import BaseHTTPMiddleware
from exceptions.exceptions import (
    NotAllowedInDemoError,
)
from fast_api.routes.fastapi_resolve_info import FastAPIResolveInfo
from middleware.query_mapping import path_query_map
from submodules.model.business_objects import general
from controller.auth import manager as auth_manager

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class DatabaseSessionHandler(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        info = self._prepare_info(request)

        request.state.session_token = general.get_ctx_token()
        info.context = {"request": request}
        request.state.info = info

        if request.url.hostname != "localhost" or request.url.port != 7051:
            access_response = self._check_access(request, info)
            if access_response is not None:
                return access_response

        try:
            response = await call_next(request)
        finally:
            general.remove_and_refresh_session(request.state.session_token)

        return response

    def _check_access(self, request, info):
        try:
            auth_manager.check_demo_access(info)
        except NotAllowedInDemoError:
            general.remove_and_refresh_session(request.state.session_token)
            return JSONResponse(
                status_code=401,
                content={"message": "Unauthorized access"},
            )
        except GraphQLError as e:
            general.remove_and_refresh_session(request.state.session_token)
            return JSONResponse(
                status_code=400,
                content={"message": e.message},
            )
        except ValueError as e:
            general.remove_and_refresh_session(request.state.session_token)
            return JSONResponse(
                status_code=400,
                content={"message": str(e)},
            )
        except Exception:
            general.remove_and_refresh_session(request.state.session_token)
            return JSONResponse(
                status_code=500,
                content={"message": "Internal server error"},
            )

        return None

    def _prepare_info(self, request):
        field_name = None
        parent_type = None

        for path, query in path_query_map.items():
            if path in request.url.path:
                field_name = query

        if request.method == "GET":
            parent_type = "Query"
        else:
            parent_type = "Mutation"

        return FastAPIResolveInfo(
            context={"request": None},
            field_name=field_name,
            parent_type=parent_type,
        )
