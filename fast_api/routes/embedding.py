from typing import List, Optional

from fast_api.routes.client_response import pack_json_result
from controller.misc import manager as misc
from fastapi import APIRouter, Request
from controller.auth import manager as auth_manager
from controller.embedding import manager
from util import spacy_util
import json

router = APIRouter()


@router.get("/embedding-platforms")
def get_embedding_platforms():
    data = manager.get_terms_info()
    return pack_json_result({"data": {"embeddingPlatforms": data}})


@router.get("/recommended-encoders")
def data_slices(request: Request, project_id: Optional[str] = None) -> List:
    if project_id:
        auth_manager.check_project_access(request.state.info, project_id)
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
