from pydantic import BaseModel


# in Measure class
class MeasureType(str, Enum):
    elevate_properties: "elevate_properties"
    buyout: "buyout"


class MeasureModel(BaseModel):
    name: str
    long_name: str
    type: MeasureType


# in ImpactMeasure class
class SelectionType(str, Enum):
    aggregation_area: "aggregation_area"
    polygon: "polygon"


class ImpactMeasureModel(BaseModel):
    selection_type: SelectionType
    property_type: str
