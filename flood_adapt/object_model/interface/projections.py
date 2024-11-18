from typing import Optional

from pydantic import BaseModel, Field

from flood_adapt.object_model.interface.object_model import IObject, IObjectModel
from flood_adapt.object_model.interface.path_builder import (
    ObjectDir,
)
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulLength,
    UnitfulLengthRefValue,
    UnitTypesLength,
)


class PhysicalProjectionModel(BaseModel):
    sea_level_rise: UnitfulLength = UnitfulLength(
        value=0.0, units=UnitTypesLength.meters
    )
    subsidence: UnitfulLength = UnitfulLength(value=0.0, units=UnitTypesLength.meters)
    rainfall_multiplier: float = Field(default=1.0, ge=0.0)
    storm_frequency_increase: float = 0.0


class SocioEconomicChangeModel(BaseModel):
    population_growth_existing: Optional[float] = 0.0
    economic_growth: Optional[float] = 0.0

    population_growth_new: Optional[float] = 0.0
    new_development_elevation: Optional[UnitfulLengthRefValue] = None
    new_development_shapefile: Optional[str] = None


class ProjectionModel(IObjectModel):
    physical_projection: PhysicalProjectionModel
    socio_economic_change: SocioEconomicChangeModel


class IProjection(IObject[ProjectionModel]):
    attrs: ProjectionModel
    dir_name = ObjectDir.projection
