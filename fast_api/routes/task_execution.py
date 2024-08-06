from controller.attribute import manager as attribute_manager
from controller.zero_shot import manager as zero_shot_manager
from controller.payload import manager as payload_manager
from fast_api.models import (
    AttributeCalculationTaskExecutionBody,
    InformationSourceTaskExecutionBody,
)
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from util import daemon
from submodules.model.enums import PayloadState, InformationSourceType

router = APIRouter()

SILENT_SUCCESS_RESPONSE = JSONResponse(
    status_code=status.HTTP_200_OK,
    content={"message": "Success"},
)


@router.get("/ping")
def ping():
    return "pong"


@router.post(
    "/{project_id}/attribute-calculation",
)
def calculate_attributes(
    project_id: str,
    attribute_calculation_task_execution: AttributeCalculationTaskExecutionBody,
):
    daemon.run(
        attribute_manager.calculate_user_attribute_all_records,
        project_id,
        attribute_calculation_task_execution.user_id,
        attribute_calculation_task_execution.attribute_id,
    )

    return SILENT_SUCCESS_RESPONSE


@router.post(
    "/information-source",
)
def information_source(
    project_id: str,
    information_source_task_execution: InformationSourceTaskExecutionBody,
):
    project_id = information_source_task_execution.project_id
    information_source_id = information_source_task_execution.information_source_id
    information_source_type = information_source_task_execution.information_source_type
    user_id = information_source_task_execution.user_id
    if information_source_type == InformationSourceType.ZERO_SHOT.value:
        zero_shot_manager.start_zero_shot_for_project_thread(
            project_id, information_source_id, user_id
        )
    else:
        payload_manager.create_payload(project_id, information_source_id, user_id)

    return SILENT_SUCCESS_RESPONSE
