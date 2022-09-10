from typing import Any, Optional

from controller.embedder_payload import payload_scheduler
from submodules.model import EmbedderPayload
from submodules.model.business_objects import embedder_payload


def get_payload(project_id: str, payload_id: str) -> EmbedderPayload:
    return embedder_payload.get(project_id, payload_id)


def create_payload(
    info,
    project_id: str,
    embedder_id: str,
    user_id: str,
    asynchronous: Optional[bool] = True,
) -> EmbedderPayload:
    return payload_scheduler.create_payload(
        info, project_id, embedder_id, user_id, asynchronous
    )
