from typing import Optional

from pydantic import BaseModel

from flood_adapt.object_model.io.unitfulvalue import UnitfulLengthRefValue


class SocioEconomicChangeModel(BaseModel):
    population_growth_existing: Optional[float] = 0
    economic_growth: Optional[float] = 0

    population_growth_new: Optional[float]
    new_development_elevation: Optional[UnitfulLengthRefValue]
    new_development_shapefile: Optional[str]


class SocioEconomicChange:
    """The Projection class containing various risk drivers."""

    def __init__(self, data: dict):
        self.attrs = SocioEconomicChangeModel.parse_obj(data)

    def __init__(self, data: dict):
        self.attrs = SocioEconomicChangeModel.parse_obj(data)
