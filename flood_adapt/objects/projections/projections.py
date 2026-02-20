import math
import os
from pathlib import Path
from typing import Optional

import geopandas as gpd
from pydantic import BaseModel, Field, PrivateAttr, field_serializer, model_validator

from flood_adapt.misc.utils import path_exists_and_absolute
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
    _gdf: gpd.GeoDataFrame | None = PrivateAttr(default=None)

    @model_validator(mode="after")
    def validate_selection_type(self) -> "SocioEconomicChange":
        if not math.isclose(self.population_growth_new or 0.0, 0.0, abs_tol=1e-8):
            if self.new_development_shapefile is None:
                raise ValueError(
                    "If `population_growth_new` is non-zero, then `new_development_shapefile` must also be provided."
                )
        return self

    @field_serializer("new_development_shapefile")
    def serialize_new_development_shapefile(
        self, value: Optional[str]
    ) -> Optional[str]:
        """Serialize the new_development_shapefile attribute to a string of only the file name."""
        if value is None:
            return None
        return Path(value).name

    def _post_load(
        self, file_path: Path | str | os.PathLike, force: bool = False, **kwargs
    ) -> None:
        if self.new_development_shapefile is not None:
            path = (
                Path(self.new_development_shapefile).name
                if force
                else self.new_development_shapefile
            )
            self.new_development_shapefile = path_exists_and_absolute(
                path, file_path
            ).as_posix()

    def read_gdf(self, reload: bool = False) -> gpd.GeoDataFrame | None:
        if self._gdf is not None and not reload:
            return self._gdf
        if self.new_development_shapefile is not None:
            self._gdf = gpd.read_file(self.new_development_shapefile)
        return self._gdf

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        if self.new_development_shapefile:
            gdf = self.read_gdf()
            if gdf is None:
                raise ValueError(
                    "The socio-economic change has a new development shapefile path, but the GeoDataFrame could not be read."
                )
            filename = Path(self.new_development_shapefile).name
            path = Path(output_dir, filename)
            gdf.to_file(path)


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
        self.socio_economic_change.save_additional(output_dir)

    def _post_load(
        self, file_path: Path | str | os.PathLike, force: bool = False, **kwargs
    ) -> None:
        self.socio_economic_change._post_load(file_path)
