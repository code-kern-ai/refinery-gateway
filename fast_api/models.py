from typing import List
from pydantic import BaseModel, StrictBool, StrictFloat, StrictInt, StrictStr


"""
Reusable Pydantic models for FastAPI.
"""


class StringBody(BaseModel):
    value: StrictStr


class IntBody(BaseModel):
    value: StrictInt


class FloatBody(BaseModel):
    value: StrictFloat


class BoolBody(BaseModel):
    value: StrictBool


class StringListBody(BaseModel):
    values: List[StrictStr]


class IntListBody(BaseModel):
    values: List[StrictInt]


class FloatListBody(BaseModel):
    values: List[StrictFloat]


class BoolListBody(BaseModel):
    values: List[StrictBool]


class UploadCredentialsAndIdBody(BaseModel):
    file_name: StrictStr
    file_type: StrictStr
    file_import_options: StrictStr
    upload_type: StrictStr
    key: StrictStr = None
