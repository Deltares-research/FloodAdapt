import os
from abc import ABC, abstractmethod
from typing import Any, Optional, Union

import geopandas as gpd
from hydromt_fiat.fiat import FiatModel

from flood_adapt.object_model.interface.site import ISite
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulArea,
    UnitfulHeight,
)

from .objectModel import IDbsObject, DbsObjectModel


class IMeasure(ABC):
    """This is a class for a FloodAdapt measure"""

    @abstractmethod
    def get_measure_type(self) -> str:
        """Returns the type of the measure

        Returns
        -------
        str
            The type of the measure
        """
        ...


class IImpactMeasure(ABC):

    @abstractmethod
    def get_object_ids(self, fiat_model: Optional[FiatModel] = None) -> list[Any]:
        """Get ids of objects that are affected by the measure.

        Returns
        -------
        list[Any]
            list of ids
        """
        ...

class IGreenInfrastructure(ABC):
    """This is a class for a FloodAdapt green infrastructure measure"""

    @staticmethod
    @abstractmethod
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
        ...

    @staticmethod
    @abstractmethod
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
        ...
