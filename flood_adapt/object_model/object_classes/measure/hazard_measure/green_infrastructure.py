import geopandas as gpd
import pyproj

from flood_adapt.object_model.interface.measures import (
    IGreenInfrastructure,
)
from flood_adapt.object_model.interface.site import ISite
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulArea,
    UnitfulHeight,
)
from flood_adapt.object_model.models.measures import GreenInfrastructureModel
from flood_adapt.object_model.object_classes.measure.hazard_measure.hazard_measure import (
    HazardMeasure,
)


class GreenInfrastructure(HazardMeasure, IGreenInfrastructure):
    """Subclass of HazardMeasure describing the measure of urban green infrastructure with a specific storage volume that is calculated based on are, storage height and percentage of area coverage"""

    _attrs = GreenInfrastructureModel

    @staticmethod
    def calculate_volume(
        area: UnitfulArea,
        height: UnitfulHeight,
        percent_area: float = 100.0,
    ) -> float:
        """Determine volume from area of the polygon and infiltration height

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
