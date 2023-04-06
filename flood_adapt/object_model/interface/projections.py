import os
from abc import ABC, abstractmethod
from typing import Any, Optional, Union

from pydantic import BaseModel

from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulLength,
    UnitfulLengthRefValue,
    UnitTypesLength,
)


class PhysicalProjectionModel(BaseModel):
    sea_level_rise: Optional[UnitfulLength] = UnitfulLength(
        value=0.0, units=UnitTypesLength.meters
    )
    subsidence: Optional[UnitfulLength] = UnitfulLength(
        value=0.0, units=UnitTypesLength.meters
    )
    rainfall_increase: Optional[float] = 0.0
    storm_frequency_increase: Optional[float] = 0.0


class SocioEconomicChangeModel(BaseModel):
    population_growth_existing: Optional[float] = 0.0
    economic_growth: Optional[float] = 0.0

    population_growth_new: Optional[float] = 0.0
    new_development_elevation: Optional[UnitfulLengthRefValue]
    new_development_shapefile: Optional[str]


class ProjectionModel(BaseModel):
    name: str
    long_name: str
    physical_projection: PhysicalProjectionModel
    socio_economic_change: SocioEconomicChangeModel


class IProjection(ABC):
    attrs: ProjectionModel

    @staticmethod
    @abstractmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """get Projection attributes from toml file"""
        ...

    @staticmethod
    @abstractmethod
    def load_dict(data: dict[str, Any]):
        """get Projection attributes from an object, e.g. when initialized from GUI"""
        ...

    @abstractmethod
    def save(self, filepath: Union[str, os.PathLike]):
        """save Projection attributes to a toml file"""
