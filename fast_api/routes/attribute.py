from controller.attribute import manager
from controller.auth import manager as auth_manager
from typing import List, Union
from fast_api.models import DeleteUserAttributeBody
from fast_api.routes.client_response import pack_json_result
from fastapi import APIRouter, Body, Depends, Query, Request
from submodules.model.enums import NotificationType
from submodules.model.util import sql_alchemy_to_dict
from util.notification import create_notification

router = APIRouter()

ALL_ATTRIBUTES_WHITELIST = {
    "id",
    "name",
    "data_type",
    "is_primary_key",
    "relative_position",
    "user_created",
    "source_code",
    "state",
    "logs",
    "visibility",
}


@router.get(
    "/{project_id}/all-attributes",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_attributes(
    project_id: str,
    state_filter: Union[List[str], None] = Query(default=None),
):
    data = manager.get_all_attributes(project_id, state_filter)
    data_dict = sql_alchemy_to_dict(data, column_whitelist=ALL_ATTRIBUTES_WHITELIST)
    return pack_json_result({"data": {"attributesByProjectId": data_dict}})


@router.get(
    "/{project_id}/check-composite-key",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_check_composite_key(
    request: Request,
    project_id: str,
):
    user = auth_manager.get_user_by_info(request.state.info)
    is_valid = manager.check_composite_key(project_id)
    if not is_valid:
        create_notification(
            NotificationType.INVALID_PRIMARY_KEY,
            user.id,
            project_id,
        )

    return pack_json_result({"data": {"checkCompositeKey": is_valid}})


@router.get(
    "/{project_id}/{attribute_id}/sample-records",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def get_sample_records(
    project_id: str,
    attribute_id,
):

    record_ids, calculated_attributes = manager.calculate_user_attribute_sample_records(
        project_id, attribute_id
    )
    return pack_json_result(
        {
            "data": {
                "calculateUserAttributeSampleRecords": {
                    "record_ids": record_ids,
                    "calculated_attributes": calculated_attributes,
                }
            }
        }
    )


@router.delete(
    "/{project_id}/delete-user-attribute",
    dependencies=[Depends(auth_manager.check_project_access_dep)],
)
def delete_user_attribute(
    request: Request,
    project_id: str,
    body: DeleteUserAttributeBody = Body(...),
):
    manager.delete_attribute(project_id, body.attribute_id)
    return pack_json_result({"data": {"deleteUserAttribute": {"ok": True}}})
