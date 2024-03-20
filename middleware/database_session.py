import logging
from starlette.middleware.base import BaseHTTPMiddleware

from fast_api.routes.fastapi_resolve_info import FastAPIResolveInfo
from middleware.query_mapping import path_query_map
from route_prefix import PREFIX_ATTRIBUTE, PREFIX_PROJECT, PREFIX_DATA_SLICE
from submodules.model.business_objects import general
from controller.auth import manager as auth_manager

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

project_access_prefix = [PREFIX_PROJECT, PREFIX_ATTRIBUTE, PREFIX_DATA_SLICE]


class DatabaseSessionHandler(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request, call_next):
        info = self._prepare_info(request)

        request.state.session_token = general.get_ctx_token()
        info.context = {"request": request}

        self._check_access(request, info)

        request.state.session_token = general.get_ctx_token()
        info.context = {"request": request}
        request.state.info = info

        try:
            response = await call_next(request)
        finally:
            general.remove_and_refresh_session(request.state.session_token)

        return response

    def _check_access(self, request, info):
        try:
            auth_manager.check_demo_access(info)
            for prefix in project_access_prefix:
                if prefix in request.url.path:
                    most_likely_url_part: str = request.url.path.replace(prefix, "")
                    url_split = most_likely_url_part.split("/")
                    project_id = url_split[0]
                    most_likely_url_part = url_split[1]
                    if project_id:
                        auth_manager.check_project_access(info, project_id)
                    break
        finally:
            general.remove_and_refresh_session(request.state.session_token)

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
