import logging
import graphene
from api.project import ProjectDetails
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
from submodules.model.models import Base
from submodules.model.session import engine

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


Base.metadata.create_all(bind=engine)
routes = [
    Route(
        "/graphql/",
        GraphQLApp(
            schema=graphene.Schema(query=schema.Query, mutation=schema.Mutation)
        ),
    ),
    Route("/notify/{path:path}", Notify),
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
]

middleware = [Middleware(DatabaseSessionHandler)]

app = Starlette(routes=routes, middleware=middleware)
