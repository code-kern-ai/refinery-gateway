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
from fast_api.routes.organization import router as organization_router
from middleware.database_session import DatabaseSessionHandler
from starlette.applications import Starlette
from starlette.graphql import GraphQLApp
from starlette.middleware import Middleware
from starlette.routing import Route, Mount

from graphql_api import schema
from controller.task_queue.task_queue import init_task_queues
from controller.project.manager import check_in_deletion_projects
from util import security, clean_up


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

PREFIX = "/api/v1"
PREFIX_ORGANIZATION = PREFIX + "/organization"

fastapi_app = FastAPI()

fastapi_app.include_router(
    organization_router, prefix=PREFIX_ORGANIZATION, tags=["organization"]
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
