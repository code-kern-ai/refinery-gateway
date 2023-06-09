from controller.embedding import connector
from submodules.model import enums
from submodules.model.business_objects import agreement, embedding, general
from submodules.model.models import Embedding
from util import daemon


def has_encoder_running(project_id: str) -> bool:
    return embedding.get_first_running_encoder(project_id) is not None


def recreate_embedding(
    project_id: str, embedding_id: str
) -> Embedding:
    old_embedding_item = embedding.get(project_id, embedding_id)
    agreement_item = agreement.get_by_xfkey(project_id, old_embedding_item.id) 
    new_embedding_item = embedding.create(
        project_id,
        old_embedding_item.attribute_id,
        old_embedding_item.name,
        enums.EmbeddingState.INITIALIZING.value,
        type=old_embedding_item.type,
        model=old_embedding_item.model,
        platform=old_embedding_item.platform,
        api_token=old_embedding_item.api_token,
        with_commit=False
    )
    old_embedding_id = old_embedding_item.id
    embedding.delete(project_id, embedding_id, with_commit=False)
    embedding.delete_tensors(embedding_id, with_commit=False)
    agreement_item.xfkey = new_embedding_item.id
    general.commit()
    connector.request_deleting_embedding(project_id, old_embedding_id)
    daemon.run(
        connector.request_embedding,
        project_id,
        new_embedding_item.id
    )
    return new_embedding_item