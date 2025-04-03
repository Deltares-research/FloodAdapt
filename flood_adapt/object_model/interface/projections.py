import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from flood_adapt.object_model.interface.object_model import IObjectModel
from flood_adapt.object_model.io import unit_system as us
from flood_adapt.object_model.utils import resolve_filepath, save_file_to_database


class PhysicalProjectionModel(BaseModel):
    sea_level_rise: us.UnitfulLength = us.UnitfulLength(
        value=0.0, units=us.UnitTypesLength.meters
    )
    subsidence: us.UnitfulLength = us.UnitfulLength(
        value=0.0, units=us.UnitTypesLength.meters
    )
    rainfall_multiplier: float = Field(default=1.0, ge=0.0)
    storm_frequency_increase: float = 0.0


class SocioEconomicChangeModel(BaseModel):
    population_growth_existing: Optional[float] = 0.0
    economic_growth: Optional[float] = 0.0

    population_growth_new: Optional[float] = 0.0
    new_development_elevation: Optional[us.UnitfulLengthRefValue] = None
    new_development_shapefile: Optional[str] = None


class Projection(IObjectModel):
    physical_projection: PhysicalProjectionModel
    socio_economic_change: SocioEconomicChangeModel

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        if self.socio_economic_change.new_development_shapefile:
            src_path = resolve_filepath(
                "projections",
                self.name,
                self.socio_economic_change.new_development_shapefile,
            )
            path = save_file_to_database(src_path, Path(output_dir))

            # Update the shapefile path in the object so it is saved in the toml file as well
            self.socio_economic_change.new_development_shapefile = path.name
