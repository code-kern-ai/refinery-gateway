from typing import List
from pydantic import BaseModel, StrictBool, StrictFloat, StrictInt, StrictStr


"""
Pydantic models for FastAPI.
"""


class StringBody(BaseModel):
    value: StrictStr


class UpdateDataSliceBody(BaseModel):
    data_slice_id: StrictStr
    static: StrictBool
    filter_raw: StrictStr
    filter_data: List[StrictStr]
