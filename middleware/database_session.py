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
from submodules.model.enums import AdminLogLevel, try_parse_enum_value
from controller.auth import manager as auth_manager
from datetime import datetime
from middleware import log_storage

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def handle_db_session(request: Request, call_next):
    info = _prepare_info(request)
    await request.body()

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
    try:
        response = await call_next(request)
    finally:
        if log_request:
            # after call next so the path_params are mapped
            await _log_request(request)
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


async def _log_request(request):
    log_request = auth_manager.extract_state_info(request, "log_request")
    log_lvl: AdminLogLevel = try_parse_enum_value(log_request, AdminLogLevel, False)
    # lazy boolean resolution to avoid unnecessary calls
    if (
        not log_lvl
        or not log_lvl.log_me(request.method)
        or (log_lvl == AdminLogLevel.NO_GET and hasattr(request.state, "get_like"))
    ):
        return

    data = None
    length = request.headers.get("content-length")
    if length and int(length) > 0:
        if request.headers.get("Content-Type") == "application/json":
            data = await request.json()
        else:
            data = await request.body()
    now = datetime.now()
    org_id = auth_manager.extract_state_info(request, "organization_id")
    log_path = f"/logs/admin/{org_id}/{now.strftime('%Y-%m-%d')}.csv"
    log_entry = {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S.%f"),
        "user_id": auth_manager.extract_state_info(request, "user_id"),
        "gateway": "REFINERY",
        "method": str(request.method),
        "path": str(request.url.path),
        "query_params": dict(request.query_params),
        "path_params": dict(request.path_params),  # only after call next possible
        "data": data,
    }
    log_storage.add_to_persist_queue(log_path, log_entry)
