from pydantic import BaseModel

class UnitfulValue(BaseModel):
    value: float
    units: str