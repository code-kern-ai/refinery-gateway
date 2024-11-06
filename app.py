import logging

from fastapi import FastAPI
from api.healthcheck import Healthcheck
from starlette.middleware import Middleware
from api.misc import IsDemoRest, IsManagedRest
from api.project import ProjectDetails
from api.transfer import (
    AssociationsImport,
    FileExport,
    JSONImport,
    KnowledgeBaseExport,
    Notify,
    PrepareFileImport,
    UploadTaskInfo,
    CognitionImport,
    CognitionPrepareProject,
)
from fast_api.routes.organization import router as org_router
from fast_api.routes.project import router as project_router
from fast_api.routes.project_setting import router as project_setting_router
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
from fast_api.routes.record_ide import router as record_ide_router
from fast_api.routes.record import router as record_router
from fast_api.routes.weak_supervision import router as weak_supervision_router
from fast_api.routes.labeling_tasks import router as labeling_tasks_router
from fast_api.routes.task_execution import router as task_execution_router
from middleware.database_session import handle_db_session
from middleware.starlette_tmp_middleware import DatabaseSessionHandler
from starlette.applications import Starlette
from starlette.routing import Route, Mount

from controller.project.manager import check_in_deletion_projects
from route_prefix import (
    PREFIX_ORGANIZATION,
    PREFIX_PROJECT,
    PREFIX_PROJECT_SETTING,
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
    PREFIX_RECORD_IDE,
    PREFIX_RECORD,
    PREFIX_WEAK_SUPERVISION,
    PREFIX_LABELING_TASKS,
    PREFIX_TASK_EXECUTION,
)
from util import security, clean_up
from middleware import log_storage
from submodules.model import session

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

fastapi_app = FastAPI()

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
fastapi_app.include_router(
    record_ide_router, prefix=PREFIX_RECORD_IDE, tags=["record-ide"]
),
fastapi_app.include_router(record_router, prefix=PREFIX_RECORD, tags=["record"]),
fastapi_app.include_router(
    weak_supervision_router, prefix=PREFIX_WEAK_SUPERVISION, tags=["weak-supervision"]
)
fastapi_app.include_router(
    labeling_tasks_router, prefix=PREFIX_LABELING_TASKS, tags=["labeling-tasks"]
)

fastapi_app_internal = FastAPI()
fastapi_app_internal.include_router(
    task_execution_router, prefix=PREFIX_TASK_EXECUTION, tags=["task-execution"]
)
routes = [
    Route("/notify/{path:path}", Notify),
    Route("/healthcheck", Healthcheck),
    Route("/project/{project_id:str}", ProjectDetails),
    Route(
        "/project/{project_id:str}/knowledge_base/{knowledge_base_id:str}",
        KnowledgeBaseExport,
    ),
    Route("/project/{project_id:str}/associations", AssociationsImport),
    Route("/project/{project_id:str}/export", FileExport),
    Route("/project/{project_id:str}/import_file", PrepareFileImport),
    Route("/project/{project_id:str}/import_json", JSONImport),
    Route(
        "/project/{project_id:str}/cognition/continue/{task_id:str}", CognitionImport
    ),
    Route(
        "/project/{cognition_project_id:str}/cognition/continue/{task_id:str}/finalize",
        CognitionPrepareProject,
    ),
    Route("/project/{project_id:str}/import/task/{task_id:str}", UploadTaskInfo),
    Route("/is_managed", IsManagedRest),
    Route("/is_demo", IsDemoRest),
    Mount("/api", app=fastapi_app, name="REST API"),
    Mount(
        "/internal/api", app=fastapi_app_internal, name="INTERNAL REST API"
    ),  # task master requests
]


fastapi_app.middleware("http")(handle_db_session)

middleware = [Middleware(DatabaseSessionHandler)]
app = Starlette(routes=routes, middleware=middleware)

check_in_deletion_projects()
security.check_secret_key()
clean_up.clean_up_database()
clean_up.clean_up_disk()

session.start_session_cleanup_thread()
log_storage.start_persist_thread()
