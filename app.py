import logging

from fastapi import FastAPI
from api.healthcheck import Healthcheck
from api.misc import IsDemoRest, IsManagedRest
import graphene
from api.project import ProjectDetails, ProjectCreationFromWorkflow
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
    CognitionParseMarkdownFile,
)
from fast_api.routes.organization import router as org_router
from fast_api.routes.project import router as project_router
from fast_api.routes.misc import router as misc_router
from fast_api.routes.comment import router as comment_router
from fast_api.routes.zero_shot import router as zero_shot_router
from fast_api.routes.attribute import router as attribute_router
from middleware.database_session import DatabaseSessionHandler
from starlette.applications import Starlette
from starlette.graphql import GraphQLApp
from starlette.middleware import Middleware
from starlette.routing import Route, Mount

from graphql_api import schema
from controller.task_queue.task_queue import init_task_queues
from controller.project.manager import check_in_deletion_projects
from route_prefix import (
    PREFIX_ORG,
    PREFIX_PROJECT,
    PREFIX_MISC,
    PREFIX_COMMENT,
    PREFIX_ZERO_SHOT,
    PREFIX_ATTRIBUTE,
)
from util import security, clean_up

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

fastapi_app = FastAPI()

fastapi_app.include_router(org_router, prefix=PREFIX_ORG, tags=["organization"])
fastapi_app.include_router(project_router, prefix=PREFIX_PROJECT, tags=["project"])
fastapi_app.include_router(misc_router, prefix=PREFIX_MISC, tags=["misc"])
fastapi_app.include_router(comment_router, prefix=PREFIX_COMMENT, tags=["comment"])
fastapi_app.include_router(
    zero_shot_router, prefix=PREFIX_ZERO_SHOT, tags=["zero-shot"]
)
fastapi_app.include_router(
    attribute_router, prefix=PREFIX_ATTRIBUTE, tags=["attribute"]
)

routes = [
    Route(
        "/graphql/",
        GraphQLApp(
            schema=graphene.Schema(query=schema.Query, mutation=schema.Mutation)
        ),
    ),
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
    Route(
        "/project/{project_id:str}/cognition/datasets/{dataset_id:str}/files/{file_id:str}/queue",
        CognitionParseMarkdownFile,
    ),
    Route("/project/{project_id:str}/import/task/{task_id:str}", UploadTaskInfo),
    Route("/project", ProjectCreationFromWorkflow),
    Route("/is_managed", IsManagedRest),
    Route("/is_demo", IsDemoRest),
    Mount("/api", app=fastapi_app, name="REST API"),
]

middleware = [Middleware(DatabaseSessionHandler)]

app = Starlette(routes=routes, middleware=middleware)

init_task_queues()
check_in_deletion_projects()
security.check_secret_key()
clean_up.clean_up_database()
clean_up.clean_up_disk()
