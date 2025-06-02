from typing import Optional
from fastapi import APIRouter
from controller.record import manager
from fast_api.routes.client_response import (
    get_silent_success,
)
from fast_api.models import RecordDeletion

router = APIRouter()


@router.delete("/{project_id}/delete-records")
def delete_by_record_ids(
    project_id: str,
    body: RecordDeletion,
    as_thread: Optional[bool] = False,
):
    manager.delete_records(project_id, body.record_ids, as_thread)
    return get_silent_success()
