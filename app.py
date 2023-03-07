import logging
from api.healthcheck import DatabaseHealthcheck, Healthcheck
import graphene
from api.project import ProjectDetails, ProjectCreationFromWorkflow
from api.transfer import (
    AssociationsImport,
    FileExport,
    JSONImport,
    KnowledgeBaseExport,
    Notify,
    PrepareFileImport,
    UploadTask,
)
from middleware.database_session import DatabaseSessionHandler
from starlette.applications import Starlette
from starlette.graphql import GraphQLApp
from starlette.middleware import Middleware
from starlette.routing import Route

from graphql_api import schema

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


routes = [
    Route(
        "/graphql/",
        GraphQLApp(
            schema=graphene.Schema(query=schema.Query, mutation=schema.Mutation)
        ),
    ),
    Route("/notify/{path:path}", Notify),
    Route("/healthcheck", Healthcheck),
    Route("/healthcheck/database", DatabaseHealthcheck),
    Route("/project/{project_id:str}", ProjectDetails),
    Route(
        "/project/{project_id:str}/knowledge_base/{knowledge_base_id:str}",
        KnowledgeBaseExport,
    ),
    Route("/project/{project_id:str}/associations", AssociationsImport),
    Route("/project/{project_id:str}/export", FileExport),
    Route("/project/{project_id:str}/import_file", PrepareFileImport),
    Route("/project/{project_id:str}/import_json", JSONImport),
    Route("/project/{project_id:str}/import/task/{task_id:str}", UploadTask),
    Route("/project", ProjectCreationFromWorkflow),
]

middleware = [Middleware(DatabaseSessionHandler)]

app = Starlette(routes=routes, middleware=middleware)
