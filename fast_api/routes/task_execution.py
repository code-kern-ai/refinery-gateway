from controller.attribute import manager
from controller.auth import manager as auth_manager
from typing import List, Union
from fast_api.models import AttributeCalculationTaskExecutionBody
from fast_api.routes.client_response import pack_json_result
from fastapi import APIRouter, Body, Depends, Query, Request
from submodules.model.enums import NotificationType
from submodules.model.util import sql_alchemy_to_dict
from util.notification import create_notification

router = APIRouter()


@router.post(
    "/{project_id}/attribute-calculation",
)
def calculate_attributes(
    project_id: str,
    attribute_calculation_task_execution: AttributeCalculationTaskExecutionBody,
):
    manager.calculate_user_attribute_all_records(
        project_id,
        attribute_calculation_task_execution.user_id,
        attribute_calculation_task_execution.attribute_id,
    )
