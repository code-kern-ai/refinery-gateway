import time
from typing import Any, Dict, List, Optional

from submodules.model import enums
from submodules.model.models import Embedding
from util import daemon, notification
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


def recreate_embeddings(project_id: str, embedding_ids: Optional[List[str]] = None) -> None:
    if not embedding_ids:
        embeddings = embedding.get_all_embeddings_by_project_id(project_id)
        if len(embeddings) == 0:
            return
        embedding_ids = [str(embed.id) for embed in embeddings]
    for embedding_id in embedding_ids:
        embedding.update_embedding_state_waiting(project_id, embedding_id)
        notification.send_organization_update(
                project_id,
                f"embedding:{embedding_id}:progress:{0.0}",
            )
        notification.send_organization_update(
                project_id,
                f"embedding:{embedding_id}:state:{enums.EmbeddingState.WAITING.value}",
            )
    general.commit()
    for embedding_id in embedding_ids:
        new_id = None
        try:
            embedding_item = embedding.get(project_id, embedding_id)
            if not embedding_item:
                continue
            embedding_item = __recreate_embedding(project_id, embedding_id)
            new_id = embedding_item.id
            time.sleep(2)
            while True:
                embedding_item = general.refresh(embedding_item)
                if not embedding_item:
                    raise Exception("Embedding not found")
                elif embedding_item.state == enums.EmbeddingState.FAILED.value or embedding_item.state == enums.EmbeddingState.FINISHED.value:
                    break
                else:
                    time.sleep(1)
        except Exception as e:
            print(
                f"Error while recreating embedding for {project_id} with id {embedding_id} - {e}", flush=True
            )
            notification.send_organization_update(
                project_id,
                f"embedding:{embedding_id}:state:{enums.EmbeddingState.FAILED.value}",
            )
            old_embedding_item = embedding.get(project_id, embedding_id)
            if old_embedding_item:
                old_embedding_item.state = enums.EmbeddingState.FAILED.value
            
            if new_id:
                new_embedding_item = embedding.get(project_id, new_id)
                if new_embedding_item:
                    new_embedding_item.state = enums.EmbeddingState.FAILED.value
            general.commit()


        notification.send_organization_update(
            project_id=project_id, message="embedding:finished:all"
        )



def __recreate_embedding(
    project_id: str, embedding_id: str
) -> Embedding:
    old_embedding_item = embedding.get(project_id, embedding_id)
    old_id = old_embedding_item.id
    new_embedding_item = embedding.create(
        project_id,
        old_embedding_item.attribute_id,
        old_embedding_item.name,
        old_embedding_item.created_by,
        enums.EmbeddingState.INITIALIZING.value,
        type=old_embedding_item.type,
        model=old_embedding_item.model,
        platform=old_embedding_item.platform,
        api_token=old_embedding_item.api_token,
        with_commit=False
    )
    embedding.delete(project_id, embedding_id, with_commit=False)
    embedding.delete_tensors(embedding_id, with_commit=False)
    general.commit()

    if new_embedding_item.platform == "openai" or new_embedding_item.platform == "cohere":
        agreement_item = agreement.get_by_xfkey(project_id, old_id)
        if not agreement_item:
            new_embedding_item.state = enums.EmbeddingState.FAILED.value
            general.commit()
            raise Exception(f"No agreement found for embedding {new_embedding_item.name}")
        agreement_item.xfkey = new_embedding_item.id
        general.commit()

    connector.request_deleting_embedding(project_id, old_id)
    daemon.run(
        connector.request_embedding,
        project_id,
        new_embedding_item.id
    )
    return new_embedding_item