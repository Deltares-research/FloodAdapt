import os
from pathlib import Path

import geopandas as gpd
import pyproj

from flood_adapt.object_model.interface.config.site import Site
from flood_adapt.object_model.interface.measures import (
    GreenInfrastructureModel,
    IMeasure,
)
from flood_adapt.object_model.io import unit_system as us
from flood_adapt.object_model.utils import resolve_filepath, save_file_to_database


class GreenInfrastructure(IMeasure[GreenInfrastructureModel]):
    """Subclass of HazardMeasure describing the measure of urban green infrastructure with a specific storage volume that is calculated based on are, storage height and percentage of area coverage."""

    _attrs_type = GreenInfrastructureModel

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        if self.attrs.polygon_file:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            src_path = resolve_filepath(
                self.dir_name, self.attrs.name, self.attrs.polygon_file
            )
            path = save_file_to_database(src_path, Path(output_dir))

            # Update the shapefile path in the object so it is saved in the toml file as well
            self.attrs.polygon_file = path.name

    @staticmethod
    def calculate_volume(
        area: us.UnitfulArea,
        height: us.UnitfulHeight,
        percent_area: float = 100.0,
    ) -> float:
        """Determine volume from area of the polygon and infiltration height.

        Parameters
        ----------
        area : us.UnitfulArea
            Area of polygon with units (calculated using calculate_polygon_area)
        height : us.UnitfulHeight
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
        volume = (
            area.convert(us.UnitTypesArea.m2)
            * height.convert(us.UnitTypesLength.meters)
            * (percent_area / 100.0)
        )
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
        floatd
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
