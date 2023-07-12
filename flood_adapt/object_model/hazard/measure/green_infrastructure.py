import os
from pathlib import Path
from typing import Any, Union

import geopandas as gpd
import pyproj
import tomli
import tomli_w

from flood_adapt.object_model.hazard.measure.hazard_measure import (
    HazardMeasure,
)
from flood_adapt.object_model.interface.measures import (
    GreenInfrastructureModel,
    IGreenInfrastructure,
)
from flood_adapt.object_model.interface.site import ISite


class GreenInfrastructure(HazardMeasure, IGreenInfrastructure):
    """Subclass of HazardMeasure describing the measure of urban green infrastructure with a specific storage volume that is calculated based on are, storage height and percentage of area coverage"""

    attrs: GreenInfrastructureModel
    database_input_path: Union[str, os.PathLike]

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]) -> IGreenInfrastructure:
        """create Floodwall from toml file"""

        obj = GreenInfrastructure()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = GreenInfrastructureModel.parse_obj(toml)
        # if measure is created by path use that to get to the database path
        obj.database_input_path = Path(filepath).parents[2]
        return obj

    @staticmethod
    def load_dict(
        data: dict[str, Any], database_input_path: Union[str, os.PathLike]
    ) -> IGreenInfrastructure:
        """create Green Infrastructure from object, e.g. when initialized from GUI"""

        obj = GreenInfrastructure()
        obj.attrs = GreenInfrastructureModel.parse_obj(data)
        obj.database_input_path = database_input_path
        return obj

    def save(self, filepath: Union[str, os.PathLike]):
        """save Floodwall to a toml file"""
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)

    @staticmethod
    def calculate_volume(
        area: float, height: float = 0.0, percent_area: float = 100.0
    ) -> float:
        """Determine volume from area of the polygon and infiltration height

        Parameters
        ----------
        area : float
            Area of polygon [m2] (calculated using calculate_polygon_area)
        height : float, optional
            Water height [m], by default 0.0
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
        volume = area * height * percent_area / 100.0
        return volume

    @staticmethod
    def calculate_polygon_area(gdf: gpd.GeoDataFrame, site: ISite) -> float:
        """Calculate area of a GeoDataFrame Polygon

        Parameters
        ----------
        gdf : gpd.GeoDataFrame
            Polygon object
        site : ISite
            site config (used for CRS)

        Returns
        -------
        float
            Area [m2]
        """
        # Determine local CRS
        crs = pyproj.CRS.from_string(site.sfincs.csname)
        gdf = gdf.to_crs(crs)

        # The GeoJSON file contains only one polygon:
        polygon = gdf.geometry.iloc[0]
        # Calculate the area of the polygon
        area = polygon.area
        return area
