from controller.attribute import manager as attribute_manager
from controller.payload import manager as payload_manager
from controller.data_slice import manager as data_slice_manager
from controller.weak_supervision import manager as weak_supervision_manager
from fast_api.models import (
    AttributeCalculationTaskExecutionBody,
    InformationSourceTaskExecutionBody,
    DataSliceActionExecutionBody,
    WeakSupervisionActionExecutionBody,
)
from fastapi import APIRouter
from submodules.model import daemon
from fast_api.routes.client_response import pack_json_result, SILENT_SUCCESS_RESPONSE

router = APIRouter()


@router.post(
    "/attribute-calculation",
)
def calculate_attributes(
    attribute_calculation_task_execution: AttributeCalculationTaskExecutionBody,
):
    daemon.run_with_db_token(
        attribute_manager.calculate_user_attribute_all_records,
        attribute_calculation_task_execution.project_id,
        attribute_calculation_task_execution.organization_id,
        attribute_calculation_task_execution.user_id,
        attribute_calculation_task_execution.attribute_id,
    )

    return SILENT_SUCCESS_RESPONSE


@router.post(
    "/information-source",
)
def information_source(
    information_source_task_execution: InformationSourceTaskExecutionBody,
):

    # already threaded in managers
    payload = payload_manager.create_payload(
        information_source_task_execution.project_id,
        information_source_task_execution.information_source_id,
        information_source_task_execution.user_id,
    )
    if payload:
        payload_id = payload.id
    return pack_json_result({"payload_id": str(payload_id)}, wrap_for_frontend=False)


@router.post(
    "/data-slice",
)
def data_slice(
    data_slice_action_execution: DataSliceActionExecutionBody,
):

    daemon.run_with_db_token(
        data_slice_manager.create_outlier_slice,
        data_slice_action_execution.project_id,
        data_slice_action_execution.user_id,
        data_slice_action_execution.embedding_id,
    )

    return SILENT_SUCCESS_RESPONSE


@router.post(
    "/weak-supervision",
)
def weak_supervision(
    weak_supervision_action_execution: WeakSupervisionActionExecutionBody,
):

    daemon.run_with_db_token(
        weak_supervision_manager.run_weak_supervision,
        weak_supervision_action_execution.project_id,
        weak_supervision_action_execution.user_id,
    )

    return SILENT_SUCCESS_RESPONSE
