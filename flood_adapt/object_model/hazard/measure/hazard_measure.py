from abc import ABC
from enum import Enum

from flood_adapt.object_model.measure import MeasureModel


class HazardType(str, Enum):
    """class describing the accepted input for the variable 'type' in HazardMeasure"""

    floodwall = "floodwall"
    pump = "pump"


class HazardMeasureModel(MeasureModel):
    """BaseModel describing the expected variables and data types of attributes common to all impact measures"""

    type: HazardType
    polygon_file: str


class HazardMeasure(ABC):
    """HazardMeasure class that holds all the information for a specific measure type that affects the impact model"""

    pass
