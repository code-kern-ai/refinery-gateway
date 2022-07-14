import time
from typing import Any, Dict, List

from submodules.model import enums
from util import daemon
from . import util
from . import connector


def get_recommended_encoders() -> List[Any]:
    return connector.request_listing_recommended_encoders()


def create_attribute_level_embedding(
    project_id: str, user_id: str, attribute_id: str, embedding_handle: str
) -> None:
    daemon.run(
        connector.request_creating_attribute_level_embedding,
        project_id,
        attribute_id,
        user_id,
        embedding_handle,
    )


def create_token_level_embedding(
    project_id: str, user_id: str, attribute_id: str, embedding_handle: str
) -> None:
    daemon.run(
        connector.request_creating_token_level_embedding,
        project_id,
        attribute_id,
        user_id,
        embedding_handle,
    )


def create_embeddings_one_by_one(
    project_id: str,
    user_id: str,
    embedding_data: Dict[str, Any],
    attribute_names: Dict[str, str],
) -> None:
    daemon.run(
        __embed_one_by_one_helper,
        project_id,
        user_id,
        embedding_data,
        attribute_names,
    )


def request_tensor_upload(project_id: str, embedding_id: str) -> Any:
    connector.request_tensor_upload(project_id, embedding_id)


def delete_embedding(project_id: str, embedding_id: str) -> None:
    connector.request_deleting_embedding(project_id, embedding_id)


def __embed_one_by_one_helper(
    project_id: str,
    user_id: str,
    embedding_data: List[Dict[str, Any]],
    attribute_names: Dict[str, str],
) -> None:
    for embedding_item in embedding_data:
        splitted = embedding_item.get("name").split("-", 2)
        if embedding_item.get("type") == enums.EmbeddingType.ON_ATTRIBUTE.value:
            connector.request_creating_attribute_level_embedding(
                project_id,
                attribute_id=attribute_names[splitted[0]],
                user_id=user_id,
                config_string=splitted[2],
            )
        elif embedding_item.get("type") == enums.EmbeddingType.ON_TOKEN.value:
            connector.request_creating_token_level_embedding(
                project_id,
                attribute_id=attribute_names[splitted[0]],
                user_id=user_id,
                config_string=splitted[2],
            )
        time.sleep(10)
        while util.has_encoder_running(project_id):
            time.sleep(10)
