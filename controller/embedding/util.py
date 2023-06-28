from controller.embedding import connector
from submodules.model import enums
from submodules.model.business_objects import agreement, embedding, general
from submodules.model.models import Embedding
from util import daemon


def has_encoder_running(project_id: str) -> bool:
    return embedding.get_first_running_encoder(project_id) is not None
