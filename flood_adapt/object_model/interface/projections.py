import os
from abc import ABC, abstractmethod
from typing import Any, Optional, Union

from pydantic import BaseModel, validator

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
    rainfall_increase: float = 0.0
    storm_frequency_increase: float = 0.0


class SocioEconomicChangeModel(BaseModel):
    population_growth_existing: Optional[float] = 0.0
    economic_growth: Optional[float] = 0.0

    population_growth_new: Optional[float] = 0.0
    new_development_elevation: Optional[UnitfulLengthRefValue] = None
    new_development_shapefile: Optional[str] = None


class ProjectionModel(BaseModel):
    name: str
    description: Optional[str] = ""
    lock_count: int = 0
    physical_projection: PhysicalProjectionModel
    socio_economic_change: SocioEconomicChangeModel

    @validator("lock_count")	
    def validate_lock_count(
        cls, lock_count: int
    ) -> int:
        """Validate lock_count"""	
        if lock_count < 0:    
            raise ValueError("lock_count must be a positive integer")
        return lock_count


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
