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
