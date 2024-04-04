from typing import List, Dict
from pydantic import BaseModel, StrictBool, StrictStr


"""
Pydantic models for FastAPI.
"""


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
