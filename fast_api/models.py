from pydantic import BaseModel, StrictStr


class StringBody(BaseModel):
    value: StrictStr
