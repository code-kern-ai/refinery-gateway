from json import JSONDecodeError
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from graphql import GraphQLError
from starlette.middleware.base import BaseHTTPMiddleware

from exceptions.exceptions import NotAllowedInDemoError, NotAllowedInOpenSourceError
from fast_api.routes.fastapi_resolve_info import FastAPIResolveInfo
from middleware.query_mapping import path_query_map
from route_prefix import (
    PREFIX_ATTRIBUTE,
    PREFIX_PROJECT,
    PREFIX_DATA_SLICE,
    PREFIX_PROJECT_SETTING,
)
from submodules.model.business_objects import general
from controller.auth import manager as auth_manager

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


PROJECT_ACCESS_PREFIX = [
    PREFIX_PROJECT,
    PREFIX_PROJECT_SETTING,
    PREFIX_ATTRIBUTE,
    PREFIX_DATA_SLICE,
]


class DatabaseSessionHandler(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        info = self._prepare_info(request)

        request.state.session_token = general.get_ctx_token()
        info.context = {"request": request}
        request.state.info = info

        self._check_access(request, info)

        try:
            response = await call_next(request)
        finally:
            general.remove_and_refresh_session(request.state.session_token)

        return response

    def _check_access(self, request, info):
        try:
            auth_manager.check_demo_access(info)
            for prefix in PROJECT_ACCESS_PREFIX:
                if prefix in request.url.path:
                    most_likely_url_part: str = request.url.path.replace(prefix, "")
                    project_id = most_likely_url_part.split("/")[0]
                    if project_id:
                        auth_manager.check_project_access(info, project_id)
                    break
        except (
            NotAllowedInDemoError,
            NotAllowedInOpenSourceError,
            GraphQLError,
            JSONDecodeError,
        ) as e:
            general.remove_and_refresh_session(request.state.session_token)
            return JSONResponse(
                status_code=401,
                content={"message": e.detail},
            )
        except Exception:
            general.remove_and_refresh_session(request.state.session_token)
            return JSONResponse(
                status_code=500,
                content={"message": "Internal server error"},
            )

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
