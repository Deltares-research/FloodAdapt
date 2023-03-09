from typing import Optional

from pydantic import BaseModel

from flood_adapt.object_model.io.unitfulvalue import UnitfulLength


class PhysicalProjectionModel(BaseModel):
    sea_level_rise: Optional[UnitfulLength] = 0
    subsidence: Optional[UnitfulLength] = 0
    rainfall_increase: Optional[float] = 0
    storm_frequency_increase: Optional[float] = 0


class PhysicalProjection:
    """The Projection class containing various risk drivers."""

    def __init__(self, data: dict):
        self.attrs = PhysicalProjectionModel.parse_obj(data)
