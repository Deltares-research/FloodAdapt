import math
import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, model_validator

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
        The population growth percentage of the existing area. default=0.0
    economic_growth : float
        The economic growth percentage. default=0.0.
    population_growth_new : float
        The population growth percentage for the new development areas. default=0.0.
    new_development_elevation : Optional[us.UnitfulLengthRefValue]
        The elevation of the new development areas. default=None.
    new_development_shapefile : Optional[str]
        The path to the shapefile of the new development areas. default=None.
    """

    population_growth_existing: Optional[float] = 0.0
    economic_growth: Optional[float] = 0.0

    population_growth_new: Optional[float] = 0.0
    new_development_elevation: Optional[us.UnitfulLengthRefValue] = None
    new_development_shapefile: Optional[str] = None

    @model_validator(mode="after")
    def validate_selection_type(self) -> "SocioEconomicChange":
        if not math.isclose(self.population_growth_new or 0.0, 0.0, abs_tol=1e-8):
            if self.new_development_shapefile is None:
                raise ValueError(
                    "If `population_growth_new` is non-zero, then `new_development_shapefile` must also be provided."
                )
        return self


class Projection(Object):
    """The accepted input for a projection in FloodAdapt.

    A projection is a combination of a physical projection and a socio-economic change.

    Attributes
    ----------
    name : str
        Name of the object.
    description : str
        Description of the object. defaults to "".
    physical_projection : PhysicalProjection
        The physical projection model. Contains information about hazard drivers.
    socio_economic_change : SocioEconomicChange
        The socio-economic change model. Contains information about impact drivers.

    """

    physical_projection: PhysicalProjection = PhysicalProjection()
    socio_economic_change: SocioEconomicChange = SocioEconomicChange()

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
