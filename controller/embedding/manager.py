import time
from typing import Any, Dict, List, Optional

from submodules.model import enums
from util import daemon
from . import util
from . import connector
from controller.model_provider import manager as model_manager
from controller.project import manager as project_manager
from submodules.model.business_objects import attribute, embedding, agreement, general


def get_recommended_encoders(is_managed: bool) -> List[Any]:
    recommendations = connector.request_listing_recommended_encoders()
    if is_managed:
        existing_models = model_manager.get_model_provider_info()
    else:
        existing_models = []
    for model in existing_models:
        if not model["zero_shot_pipeline"]:
            not_yet_known = (
                len(
                    list(
                        filter(
                            lambda rec: rec["config_string"] == model["name"],
                            recommendations,
                        )
                    )
                )
                == 0
            )
            if not_yet_known:
                recommendations.append(
                    {
                        "config_string": model["name"],
                        "description": "User downloaded model",
                        "tokenizers": ["all"],
                        "applicability": {"attribute": True, "token": True},
                    }
                )
    return recommendations



def create_embedding(
    project_id: str, embedding_id: str
) -> None:
    daemon.run(
        connector.request_embedding,
        project_id,
        embedding_id
    )

def create_embeddings_one_by_one(
    project_id: str,
    embeddings_ids: List[str],
) -> None:
    daemon.run(
        __embed_one_by_one_helper,
        project_id,
        embeddings_ids
    )


def request_tensor_upload(project_id: str, embedding_id: str) -> Any:
    connector.request_tensor_upload(project_id, embedding_id)


def delete_embedding(project_id: str, embedding_id: str) -> None:
    embedding.delete(project_id, embedding_id)
    embedding.delete_tensors(embedding_id, with_commit=True)
    connector.request_deleting_embedding(project_id, embedding_id)


def __embed_one_by_one_helper(
    project_id: str,
    embeddings_ids: List[str]
) -> None:
    for embedding_id in embeddings_ids:
        connector.request_embedding(project_id, embedding_id)
        time.sleep(5)
        while util.has_encoder_running(project_id):
            time.sleep(5)


def get_embedding_name(
    project_id: str, attribute_id: str,  platform: str, embedding_type: str, model: Optional[str] = None, apiToken: Optional[str] = None
) -> str:
    if embedding_type not in [
        enums.EmbeddingType.ON_ATTRIBUTE.value,
        enums.EmbeddingType.ON_TOKEN.value,
    ]:
        raise ValueError("Embedding type must be either attribute or token")
    embedding_type = (
        "classification"
        if embedding_type == enums.EmbeddingType.ON_ATTRIBUTE.value
        else "extraction"
    )

    attribute_item = attribute.get(project_id, attribute_id)
    if attribute_item is None:
        raise ValueError("attribute not found")
    attribute_name = attribute_item.name

    name = f"{attribute_name}-{embedding_type}-{platform}"

    if model:
        name += f"-{model}"

    if apiToken:
        name += f"-{apiToken[:8]}..."
    
    return name

