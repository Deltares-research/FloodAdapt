import os
from pathlib import Path
from typing import Any

import geopandas as gpd
import pyproj

from flood_adapt.object_model.interface.measures import (
    GreenInfrastructureModel,
    HazardMeasure,
)
from flood_adapt.object_model.interface.site import Site
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulArea,
    UnitfulHeight,
)
from flood_adapt.object_model.utils import resolve_filepath, save_file_to_database


class GreenInfrastructure(HazardMeasure[GreenInfrastructureModel]):
    """Subclass of HazardMeasure describing the measure of urban green infrastructure with a specific storage volume that is calculated based on are, storage height and percentage of area coverage."""

    attrs: GreenInfrastructureModel

    def __init__(self, data: dict[str, Any]) -> None:
        if isinstance(data, GreenInfrastructureModel):
            self.attrs = data
        else:
            self.attrs = GreenInfrastructureModel.model_validate(data)

    def save_additional(self, toml_path: Path | str | os.PathLike) -> None:
        if self.attrs.polygon_file:
            src_path = resolve_filepath(
                self.dir_name, self.attrs.name, self.attrs.polygon_file
            )
            path = save_file_to_database(src_path, Path(toml_path).parent)
            # Update the shapefile path in the object so it is saved in the toml file as well
            self.attrs.polygon_file = path.name

    @staticmethod
    def calculate_volume(
        area: UnitfulArea,
        height: UnitfulHeight,
        percent_area: float = 100.0,
    ) -> float:
        """Determine volume from area of the polygon and infiltration height.

        Parameters
        ----------
        area : UnitfulArea
            Area of polygon with units (calculated using calculate_polygon_area)
        height : UnitfulHeight
            Water height with units
        percent_area : float, optional
            Percentage area covered by green infrastructure [%], by default 100.0

        Returns
        -------
        float


        Returns
        -------
        float
            Volume [m3]
        """
        volume = area.convert("m2") * height.convert("meters") * percent_area / 100.0
        return volume

    @staticmethod
    def calculate_polygon_area(gdf: gpd.GeoDataFrame, site: Site) -> float:
        """Calculate area of a GeoDataFrame Polygon.

        Parameters
        ----------
        gdf : gpd.GeoDataFrame
            Polygon object
        site : Site
            site config (used for CRS)

        Returns
        -------
        float
            Area [m2]
        """
        # Determine local CRS
        crs = pyproj.CRS.from_string(site.sfincs.csname)
        gdf = gdf.to_crs(crs)

        # The GeoJSON file can contain multiple polygons
        polygon = gdf.geometry
        # Calculate the area of all polygons
        area = polygon.area.sum()
        return area
