from controller.attribute import manager as attribute_manager
from controller.tokenization import manager as tokenization_manager
from fast_api.models import (
    AttributeCalculationTaskExecutionBody,
    TokenizationTaskExecutionBody,
)
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

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
    attribute_manager.calculate_user_attribute_all_records(
        project_id,
        attribute_calculation_task_execution.user_id,
        attribute_calculation_task_execution.attribute_id,
    )
    return SILENT_SUCCESS_RESPONSE


@router.post(
    "/{project_id}/tokenization",
)
def tokenization(
    project_id: str,
    tokenization_task_execution: TokenizationTaskExecutionBody,
):
    # tokenization_manager
    return SILENT_SUCCESS_RESPONSE
