from fast_api.routes.client_response import pack_json_result
from fastapi import APIRouter
from submodules.model.util import sql_alchemy_to_dict
from controller.embedding import manager

router = APIRouter()


@router.get("/embedding-platforms")
def get_embedding_platforms():
    data = manager.get_terms_info()
    return pack_json_result({"data": {"embeddingPlatforms": data}})
