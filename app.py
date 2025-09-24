import logging
import os
from fastapi import FastAPI
from starlette.middleware import Middleware

from api.healthcheck import Healthcheck
from api.misc import (
    FullConfigRest,
)
from api.transfer import (
    Notify,
)
from config_handler import (
    init_config,
)

from fast_api.routes.organization import router as org_router
from fast_api.routes.project import router as project_router
from fast_api.routes.project_setting import router as project_setting_router
from fast_api.routes.project_internal import router as project_internal_router
from fast_api.routes.misc import router as misc_router
from fast_api.routes.comment import router as comment_router
from fast_api.routes.attribute import router as attribute_router
from fast_api.routes.embedding import router as embedding_router
from fast_api.routes.notification import router as notification_router
from fast_api.routes.data_slices import router as data_slice_router
from fast_api.routes.lookup_lists import router as lookup_lists_router
from fast_api.routes.heuristic import router as heuristic_router
from fast_api.routes.data_browser import router as data_browser_router
from fast_api.routes.labeling import router as labeling_router
from fast_api.routes.record import router as record_router
from fast_api.routes.weak_supervision import router as weak_supervision_router
from fast_api.routes.labeling_tasks import router as labeling_tasks_router
from fast_api.routes.task_execution import router as task_execution_router
from fast_api.routes.record_internal import router as record_internal_router
from fast_api.routes.playground import router as playground_router
from middleware.database_session import handle_db_session
from middleware.starlette_tmp_middleware import DatabaseSessionHandler
from starlette.applications import Starlette
from starlette.routing import Route, Mount

from controller.project.manager import check_in_deletion_projects
from controller.user.manager import migrate_kratos_users
from route_prefix import (
    PREFIX_ORGANIZATION,
    PREFIX_PROJECT,
    PREFIX_PROJECT_SETTING,
    PREFIX_PROJECT_INTERNAL,
    PREFIX_MISC,
    PREFIX_COMMENT,
    PREFIX_ATTRIBUTE,
    PREFIX_EMBEDDING,
    PREFIX_NOTIFICATION,
    PREFIX_DATA_SLICE,
    PREFIX_LOOKUP_LISTS,
    PREFIX_HEURISTIC,
    PREFIX_DATA_BROWSER,
    PREFIX_LABELING,
    PREFIX_RECORD,
    PREFIX_RECORD_INTERNAL,
    PREFIX_WEAK_SUPERVISION,
    PREFIX_LABELING_TASKS,
    PREFIX_TASK_EXECUTION,
    PREFIX_PLAYGROUND,
)
from util import security, clean_up
from middleware import log_storage
from submodules.model import session, telemetry
from controller.sums_table import manager as sums_table_manager

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

OTLP_GRPC_ENDPOINT = os.getenv("OTLP_GRPC_ENDPOINT", "tempo:4317")

init_config()
migrate_kratos_users()

app_name = "refinery-gateway"
fastapi_app = FastAPI(title=app_name)

fastapi_app.include_router(
    org_router, prefix=PREFIX_ORGANIZATION, tags=["organization"]
)
fastapi_app.include_router(project_router, prefix=PREFIX_PROJECT, tags=["project"])
fastapi_app.include_router(
    project_setting_router, prefix=PREFIX_PROJECT_SETTING, tags=["project-setting"]
)
fastapi_app.include_router(misc_router, prefix=PREFIX_MISC, tags=["misc"])
fastapi_app.include_router(comment_router, prefix=PREFIX_COMMENT, tags=["comment"])
fastapi_app.include_router(
    attribute_router, prefix=PREFIX_ATTRIBUTE, tags=["attribute"]
)
fastapi_app.include_router(
    embedding_router, prefix=PREFIX_EMBEDDING, tags=["embedding"]
)
fastapi_app.include_router(
    notification_router, prefix=PREFIX_NOTIFICATION, tags=["notification"]
)
fastapi_app.include_router(
    data_slice_router, prefix=PREFIX_DATA_SLICE, tags=["data-slice"]
)
fastapi_app.include_router(
    lookup_lists_router, prefix=PREFIX_LOOKUP_LISTS, tags=["lookup-lists"]
)
fastapi_app.include_router(
    heuristic_router, prefix=PREFIX_HEURISTIC, tags=["heuristic"]
)
fastapi_app.include_router(
    data_browser_router, prefix=PREFIX_DATA_BROWSER, tags=["data-browser"]
)
fastapi_app.include_router(labeling_router, prefix=PREFIX_LABELING, tags=["labeling"])
fastapi_app.include_router(record_router, prefix=PREFIX_RECORD, tags=["record"]),
fastapi_app.include_router(
    weak_supervision_router, prefix=PREFIX_WEAK_SUPERVISION, tags=["weak-supervision"]
)
fastapi_app.include_router(
    labeling_tasks_router, prefix=PREFIX_LABELING_TASKS, tags=["labeling-tasks"]
)
fastapi_app.include_router(
    playground_router, prefix=PREFIX_PLAYGROUND, tags=["playground"]
)

app_name_internal = app_name + "-i"
fastapi_app_internal = FastAPI(title=app_name_internal)

fastapi_app_internal.include_router(
    task_execution_router, prefix=PREFIX_TASK_EXECUTION, tags=["task-execution"]
)

fastapi_app_internal.include_router(
    record_internal_router, prefix=PREFIX_RECORD_INTERNAL, tags=["record-internal"]
)
fastapi_app_internal.include_router(
    project_internal_router, prefix=PREFIX_PROJECT_INTERNAL, tags=["project-internal"]
)


routes = [
    Route("/full_config", FullConfigRest),
    Route("/notify/{path:path}", Notify),
    Route("/healthcheck", Healthcheck),
    Mount("/api", app=fastapi_app, name="REST API"),
    Mount(
        "/internal/api", app=fastapi_app_internal, name="INTERNAL REST API"
    ),  # task master requests
]


fastapi_app.middleware("http")(handle_db_session)

if telemetry.ENABLE_TELEMETRY:
    print("WARNING:  Running telemetry.", flush=True)
    telemetry.setting_otlp(fastapi_app, app_name=app_name, endpoint=OTLP_GRPC_ENDPOINT)
    fastapi_app.add_middleware(telemetry.PrometheusMiddleware, app_name=app_name)
    fastapi_app.add_route("/metrics", telemetry.metrics)

    # -------- internal --------
    app_name += "-i"
    telemetry.setting_otlp(
        fastapi_app_internal, app_name=app_name_internal, endpoint=OTLP_GRPC_ENDPOINT
    )
    fastapi_app_internal.add_middleware(
        telemetry.PrometheusMiddleware, app_name=app_name_internal
    )
    fastapi_app_internal.add_route("/metrics", telemetry.metrics)

    # Filter out /metrics
    logging.getLogger("uvicorn.access").addFilter(
        lambda record: not any(
            item in record.getMessage()
            for item in ("GET /api/metrics", "GET /internal/api/metrics")
        )
    )

middleware = [Middleware(DatabaseSessionHandler)]
app = Starlette(routes=routes, middleware=middleware)

check_in_deletion_projects()
security.check_secret_key()
clean_up.clean_up_database()
clean_up.clean_up_disk()

session.start_session_cleanup_thread()
log_storage.start_persist_thread()
sums_table_manager.start_sums_table_thread()
