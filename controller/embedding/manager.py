import time
from typing import Any, List, Optional, Union, Dict
from exceptions.exceptions import ApiTokenImportError

from submodules.model import enums
from submodules.model.models import Embedding
from util import daemon, notification
from . import util
from . import connector
from .terms import TERMS_INFO
from controller.model_provider import manager as model_manager
from submodules.model.business_objects import (
    attribute,
    embedding,
    agreement,
    general,
    project,
)
from submodules.model.util import sql_alchemy_to_dict
from controller.embedding.connector import collection_on_qdrant


def get_terms_info(
    platform: Optional[enums.EmbeddingPlatform] = None,
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    if platform:
        return TERMS_INFO[platform.value]
    return list(TERMS_INFO.values())


def get_current_terms_text(
    platform: str,
) -> Optional[str]:
    terms = TERMS_INFO[platform]
    term_text = terms.get("terms")
    if not term_text:
        return None
    link = terms.get("link")
    if link:
        term_text = term_text.replace("@@PLACEHOLDER@@", link)
    return term_text


def get_recommended_encoders(is_managed: bool) -> List[Any]:
    # only use is_managed if it is really managed
    # can run into circular import problems if directly resolved here by helper method
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


def create_embedding(project_id: str, embedding_id: str) -> None:
    daemon.run(connector.request_embedding, project_id, embedding_id)


def create_embeddings_one_by_one(
    project_id: str,
    embeddings_ids: List[str],
) -> None:
    daemon.run(__embed_one_by_one_helper, project_id, embeddings_ids)


def request_tensor_upload(project_id: str, embedding_id: str) -> Any:
    connector.request_tensor_upload(project_id, embedding_id)


def delete_embedding(project_id: str, embedding_id: str) -> None:
    embedding.delete(project_id, embedding_id)
    embedding.delete_tensors(embedding_id, with_commit=True)
    connector.request_deleting_embedding(project_id, embedding_id)


def __embed_one_by_one_helper(project_id: str, embeddings_ids: List[str]) -> None:
    ctx_token = general.get_ctx_token()
    for embedding_id in embeddings_ids:
        connector.request_embedding(project_id, embedding_id)
        time.sleep(5)
        c = 1
        while util.has_encoder_running(project_id):
            c += 1
            if c > 12:
                ctx_token = general.remove_and_refresh_session(ctx_token, True)
                c = 1
            time.sleep(5)
    general.remove_and_refresh_session(ctx_token, False)


def get_embedding_name(
    project_id: str,
    attribute_id: str,
    platform: str,
    embedding_type: str,
    model: Optional[str] = None,
    api_token: Optional[str] = None,
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

    if api_token:
        name += f"-{api_token[:3]}...{api_token[-4:]}"

    return name


EMBEDDING_SCHEMA_WHITELIST = [
    "id",
    "name",
    "custom",
    "type",
    "state",
    "progress",
    "dimension",
    "count",
    "platform",
    "model",
    "filter_attributes",
    "attribute_id",
]


def get_embedding_schema(project_id: str) -> List[Dict[str, Any]]:
    embeddings = embedding.get_all_embeddings_by_project_id(project_id)
    embedding_dict = sql_alchemy_to_dict(
        embeddings, column_whitelist=EMBEDDING_SCHEMA_WHITELIST
    )
    number_records = len(project.get(project_id).records)
    expanded_embeddings = []
    for embed in embedding_dict:
        count = embedding.get_tensor_count(embed["id"])
        onQdrant = collection_on_qdrant(project_id, embed["id"])

        embedding_item = embedding.get_tensor(embed["id"])
        dimension = 0
        if embedding_item is not None:
            # distinguish between token and attribute embeddings
            if type(embedding_item.data[0]) is list:
                dimension = len(embedding_item.data[0])
            else:
                dimension = len(embedding_item.data)

        if embed["state"] == "FINISHED":
            progress = 1
        elif embed["state"] == "INITIALIZING" or embed["state"] == "WAITING":
            progress = 0.0
        else:
            progress = min(
                0.1 + (count / number_records * 0.9),
                0.99,
            )
        expanded_embed = {
            **embed,
            "progress": progress,
            "count": count,
            "dimension": dimension,
            "onQdrant": onQdrant,
        }
        expanded_embeddings.append(expanded_embed)
    return {"id": project_id, "embeddings": expanded_embeddings}


def recreate_embeddings(
    project_id: str, embedding_ids: Optional[List[str]] = None, user_id: str = None
) -> None:
    if not embedding_ids:
        embeddings = embedding.get_all_embeddings_by_project_id(project_id)
        if len(embeddings) == 0:
            return
        embedding_ids = [str(embed.id) for embed in embeddings]

    set_to_wait = False
    for embedding_id in embedding_ids:
        set_to_wait = True
        embedding.update_embedding_state_waiting(project_id, embedding_id)
    general.commit()

    if set_to_wait:
        notification.send_organization_update(
            project_id,
            f"embedding:{None}:state:{enums.EmbeddingState.WAITING.value}",
        )

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
                elif (
                    embedding_item.state == enums.EmbeddingState.FAILED.value
                    or embedding_item.state == enums.EmbeddingState.FINISHED.value
                ):
                    break
                else:
                    time.sleep(1)
        except ApiTokenImportError as e:
            notification.create_notification(
                enums.NotificationType.RECREATION_OF_EMBEDDINGS_ERROR,
                user_id,
                project_id,
            )
            __handle_failed_embedding(project_id, embedding_id, new_id, e)

        except Exception as e:
            __handle_failed_embedding(project_id, embedding_id, new_id, e)

        notification.send_organization_update(
            project_id=project_id, message="embedding:finished:all"
        )


def __handle_failed_embedding(
    project_id: str, embedding_id: str, new_id: str, e: Exception
) -> None:
    print(
        f"Error while recreating embedding for {project_id} with id {embedding_id} - {e}",
        flush=True,
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


def __recreate_embedding(project_id: str, embedding_id: str) -> Embedding:
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
        filter_attributes=old_embedding_item.filter_attributes,
        additional_data=old_embedding_item.additional_data,
        with_commit=False,
    )
    embedding.delete(project_id, embedding_id, with_commit=False)
    embedding.delete_tensors(embedding_id, with_commit=False)
    general.commit()

    if (
        new_embedding_item.platform == enums.EmbeddingPlatform.OPENAI.value
        or new_embedding_item.platform == enums.EmbeddingPlatform.COHERE.value
        or new_embedding_item.platform == enums.EmbeddingPlatform.AZURE.value
    ):
        agreement_item = agreement.get_by_xfkey(
            project_id, old_id, enums.AgreementType.EMBEDDING.value
        )
        if not agreement_item:
            new_embedding_item.state = enums.EmbeddingState.FAILED.value
            general.commit()
            raise ApiTokenImportError(
                f"No agreement found for embedding {new_embedding_item.name}"
            )
        agreement_item.xfkey = new_embedding_item.id
        general.commit()

    connector.request_deleting_embedding(project_id, old_id)
    daemon.run(connector.request_embedding, project_id, new_embedding_item.id)
    return new_embedding_item


def update_embedding_payload(
    project_id: str, embedding_id: str, filter_attributes: List[str]
) -> bool:
    notification.send_organization_update(
        project_id=project_id,
        message=f"upload_embedding_payload:{str(embedding_id)}:start",
    )
    embedding_item = embedding.get(project_id, embedding_id)
    if not embedding_item:
        return False
    # commit to ensure the values are set correct for the embedding container to request
    previous_attributes = set(embedding_item.filter_attributes)
    embedding_item.filter_attributes = filter_attributes
    general.commit()
    if connector.update_attribute_payloads_for_neural_search(project_id, embedding_id):
        embedding.update_embedding_filter_attributes(
            project_id, embedding_id, filter_attributes, with_commit=True
        )
        return True
    embedding.update_embedding_filter_attributes(
        project_id, embedding_id, previous_attributes, with_commit=True
    )
    return False


def update_label_payloads_for_neural_search(
    project_id: str, record_ids: Optional[List[str]] = None
) -> None:
    relevant_embeddings = embedding.get_finished_embeddings_by_started_at(project_id)
    connector.update_label_payloads_for_neural_search(
        project_id=project_id,
        embedding_ids=[str(e.id) for e in relevant_embeddings],
        record_ids=record_ids,
    )
