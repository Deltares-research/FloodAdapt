from abc import abstractmethod
from typing import Optional

from pydantic import BaseModel, Field

from flood_adapt.object_model.interface.object_model import IObject, IObjectModel
from flood_adapt.object_model.interface.path_builder import (
    ObjectDir,
)
from flood_adapt.object_model.io import unit_system as us


class PhysicalProjectionModel(BaseModel):
    sea_level_rise: us.UnitfulLength = us.UnitfulLength(
        value=0.0, units=us.UnitTypesLength.meters
    )
    subsidence: us.UnitfulLength = us.UnitfulLength(
        value=0.0, units=us.UnitTypesLength.meters
    )
    rainfall_multiplier: float = Field(default=1.0, ge=0.0)
    storm_frequency_increase: float = 0.0


class PhysicalProjection:
    """The Projection class containing various risk drivers."""

    attrs: PhysicalProjectionModel

    def __init__(self, data: PhysicalProjectionModel):
        self.attrs = PhysicalProjectionModel.model_validate(data)

    def __eq__(self, other):
        if not isinstance(other, PhysicalProjection):
            # don't attempt to compare against unrelated types
            return NotImplemented

        return self.attrs == other.attrs


class SocioEconomicChangeModel(BaseModel):
    population_growth_existing: Optional[float] = 0.0
    economic_growth: Optional[float] = 0.0

    population_growth_new: Optional[float] = 0.0
    new_development_elevation: Optional[us.UnitfulLengthRefValue] = None
    new_development_shapefile: Optional[str] = None


class SocioEconomicChange:
    """The Projection class containing various risk drivers."""

    def __init__(self, data: SocioEconomicChangeModel):
        self.attrs = SocioEconomicChangeModel.model_validate(data)


class ProjectionModel(IObjectModel):
    physical_projection: PhysicalProjectionModel
    socio_economic_change: SocioEconomicChangeModel


class IProjection(IObject[ProjectionModel]):
    _attrs_type = ProjectionModel
    dir_name = ObjectDir.projection
    display_name = "Projection"

    @abstractmethod
    def get_physical_projection(self) -> PhysicalProjection: ...

    @abstractmethod
    def get_socio_economic_change(self) -> SocioEconomicChange: ...
