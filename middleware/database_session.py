import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from exceptions.exceptions import (
    DatabaseSessionError,
    NotAllowedInDemoError,
)
from fast_api.routes.fastapi_resolve_info import FastAPIResolveInfo
from middleware.query_mapping import path_query_map
from submodules.model.business_objects import general
from controller.auth import manager as auth_manager
from middleware import log_storage

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def handle_db_session(request: Request, call_next):
    info = _prepare_info(request)

    request.state.session_token = general.get_ctx_token()
    info.context = {"request": request}
    request.state.info = info
    request.state.parsed = {}

    if request.url.hostname != "localhost" or request.url.port != 7051:
        access_response = _check_access(request, info)
        if access_response is not None:
            general.remove_and_refresh_session(request.state.session_token)
            return access_response

    log_request = auth_manager.extract_state_info(request, "log_request")
    length = request.headers.get("content-length")

    if log_request and length and int(length) > 0:
        await log_storage.set_request_data(request)

    try:
        response = await call_next(request)
    finally:
        if log_request:
            # after call next so the path_params are mapped
            await log_storage.log_request(request)
        general.remove_and_refresh_session(request.state.session_token)

    return response


def _check_access(request, info):
    try:
        auth_manager.check_demo_access(info)
    except NotAllowedInDemoError:
        general.remove_and_refresh_session(request.state.session_token)
        return JSONResponse(
            status_code=401,
            content={"message": "Unauthorized access"},
        )
    except DatabaseSessionError as e:
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


def _prepare_info(request):
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
