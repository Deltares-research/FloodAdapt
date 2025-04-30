import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from flood_adapt.misc.utils import resolve_filepath, save_file_to_database
from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.object_model import Object


class PhysicalProjection(BaseModel):
    """The accepted input for a physical projection in FloodAdapt.

    Attributes
    ----------
    sea_level_rise : us.UnitfulLength
        The sea level rise in meters. Default=us.UnitfulLength(0.0, us.UnitTypesLength.meters).
    subsidence : us.UnitfulLength
        The subsidence in meters. Default=us.UnitfulLength(0.0, us.UnitTypesLength.meters).
    rainfall_multiplier : float
        The rainfall multiplier. Default = 1.0.
    storm_frequency_increase : float
        The storm frequency increase as a percentage. Default = 0.0.
    """

    sea_level_rise: us.UnitfulLength = us.UnitfulLength(
        value=0.0, units=us.UnitTypesLength.meters
    )
    subsidence: us.UnitfulLength = us.UnitfulLength(
        value=0.0, units=us.UnitTypesLength.meters
    )
    rainfall_multiplier: float = Field(default=1.0, ge=0.0)
    storm_frequency_increase: float = 0.0


class SocioEconomicChange(BaseModel):
    """The accepted input for socio-economic change in FloodAdapt.

    Attributes
    ----------
    population_growth_existing : float
        The existing population growth rate. default=0.0
    economic_growth : float
        The economic growth rate. default=0.0.
    population_growth_new : float
        The population growth rate for new developments. default=0.0.
    new_development_elevation : Optional[us.UnitfulLengthRefValue]
        The elevation of new developments. default=None.
    new_development_shapefile : Optional[str]
        The path to the shapefile of new developments. default=None.
    """

    population_growth_existing: Optional[float] = 0.0
    economic_growth: Optional[float] = 0.0

    population_growth_new: Optional[float] = 0.0
    new_development_elevation: Optional[us.UnitfulLengthRefValue] = None
    new_development_shapefile: Optional[str] = None


class Projection(Object):
    """The accepted input for a projection in FloodAdapt.

    A projection is a combination of a physical projection and a socio-economic change.

    Attributes
    ----------
    physical_projection : PhysicalProjection
        The physical projection model. Contains information about hazard drivers.
    socio_economic_change : SocioEconomicChange
        The socio-economic change model. Contains information about impact drivers.

    """

    physical_projection: PhysicalProjection
    socio_economic_change: SocioEconomicChange

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
