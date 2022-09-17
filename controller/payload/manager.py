from typing import Any, Optional

from controller.payload import payload_scheduler
from submodules.model import InformationSourcePayload
from submodules.model.business_objects import payload


def get_payload(project_id: str, payload_id: str) -> InformationSourcePayload:
    return payload.get(project_id, payload_id)


def create_payload(
    info,
    project_id: str,
    information_source_id: str,
    user_id: str,
    asynchronous: Optional[bool] = True,
) -> InformationSourcePayload:
    return payload_scheduler.create_payload(
        info, project_id, information_source_id, user_id, asynchronous
    )


def create_empty_crowd_payload(
    project_id: str, information_source_id: str, user_id: str
) -> InformationSourcePayload:
    return payload.create_empty_crowd_payload(
        project_id, information_source_id, user_id
    )


def update_payload_status(
    project_id: str, payload_id: str, status: str
) -> InformationSourcePayload:
    return payload.update_status(project_id, payload_id, status)
