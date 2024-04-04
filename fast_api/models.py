from typing import List, Dict, Optional, Union
from pydantic import BaseModel, StrictBool, StrictFloat, StrictInt, StrictStr


"""
Pydantic models for FastAPI.
"""


class StringBody(BaseModel):
    value: StrictStr


class LinkRouteBody(BaseModel):
    link_route: StrictStr


class GenerateAccessLinkBody(BaseModel):
    type: StrictStr
    id: StrictStr


class LockAccessLinkBody(BaseModel):
    link_id: StrictStr
    lock_state: StrictBool


class UpdateDataSliceBody(BaseModel):
    data_slice_id: StrictStr
    static: StrictBool
    filter_raw: StrictStr
    filter_data: List[StrictStr]


class UploadCredentialsAndIdBody(BaseModel):
    file_name: StrictStr
    file_type: StrictStr
    file_import_options: StrictStr
    upload_type: StrictStr
    key: StrictStr = None


class RecordIdeBody(BaseModel):
    code: StrictStr


class RecordSyncBody(BaseModel):
    changes: Dict


class CreateHeuristicBody(BaseModel):
    labeling_task_id: StrictStr
    type: StrictStr
    description: StrictStr
    source_code: StrictStr
    name: StrictStr


class InitWeakSuperVisionBody(BaseModel):
    overwrite_default_precision: Optional[Union[StrictFloat, StrictInt]]
    overwrite_weak_supervision: Optional[Dict[str, Union[StrictFloat, StrictInt]]]


class CreateZeroShotBody(BaseModel):
    target_config: StrictStr
    labeling_task_id: StrictStr
    attribute_id: StrictStr


class UpdateHeuristicBody(BaseModel):
    labeling_task_id: StrictStr
    code: StrictStr
    description: StrictStr
    name: StrictStr


class RunThenWeakSupervisionBody(BaseModel):
    heuristic_id: StrictStr
    labeling_task_id: StrictStr


class CancelZeroShotBody(BaseModel):
    heuristic_id: StrictStr
    payload_id: StrictStr


class AddClassificationLabelBody(BaseModel):
    record_id: StrictStr
    labeling_task_id: StrictStr
    label_id: StrictStr
    as_gold_star: Optional[StrictBool]
    source_id: Optional[StrictStr]


class AddExtractionLabelBody(BaseModel):
    record_id: StrictStr
    labeling_task_id: StrictStr
    label_id: StrictStr
    as_gold_star: Optional[StrictBool]
    token_start_index: Optional[StrictInt]
    token_end_index: Optional[StrictInt]
    value: Optional[StrictStr]
    source_id: Optional[StrictStr]


class SetGoldStarBody(BaseModel):
    record_id: StrictStr
    labeling_task_id: StrictStr
    gold_user_id: StrictStr


class RemoveGoldStarBody(BaseModel):
    record_id: StrictStr
    labeling_task_id: StrictStr


class CreateOrganizationBody(BaseModel):
    name: StrictStr


class AddUserToOrganizationBody(BaseModel):
    user_mail: StrictStr
    organization_name: StrictStr


class ChangeOrganizationBody(BaseModel):
    org_id: StrictStr
    changes: StrictStr
