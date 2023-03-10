from typing import Optional

from pydantic import BaseModel

from flood_adapt.object_model.io.unitfulvalue import UnitfulLength


class PhysicalProjectionModel(BaseModel):
    sea_level_rise: Optional[UnitfulLength]  # TODO add default zero
    subsidence: Optional[UnitfulLength]
    rainfall_increase: Optional[float] = 0.0
    storm_frequency_increase: Optional[float] = 0.0


class PhysicalProjection:
    """The Projection class containing various risk drivers."""

    def __init__(self, data: PhysicalProjectionModel):
        self.attrs = PhysicalProjectionModel.parse_obj(data)
