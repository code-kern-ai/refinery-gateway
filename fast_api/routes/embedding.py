from typing import List, Optional

from fast_api.routes.client_response import pack_json_result
from controller.misc import manager as misc
from fastapi import APIRouter, Request
from controller.embedding import manager
from util import spacy_util
import json
from submodules.model.util import pack_as_graphql


router = APIRouter()


@router.get("/embedding-platforms")
def get_embedding_platforms():
    data = manager.get_terms_info()
    return pack_json_result({"data": {"embeddingPlatforms": data}})


@router.get("/recommended-encoders")
def data_slices(request: Request, project_id: Optional[str] = None) -> List:
    is_managed = misc.check_is_managed()
    data = manager.get_recommended_encoders(is_managed)
    for v in data:
        v["applicability"] = json.dumps(v["applicability"])
    return pack_json_result({"data": {"recommendedEncoders": data}})


@router.get("/language-models")
def language_models(request: Request) -> List:
    return pack_json_result(
        {"data": {"languageModels": spacy_util.get_language_models()}}
    )


@router.get("/embeddings-by-project")
def get_embeddings(request: Request, project_id: str) -> List:
    data = manager.get_embedding_schema(
        project_id,
    )
    data_graphql = pack_as_graphql(data, "projectByProjectId")
    return pack_json_result(data_graphql)