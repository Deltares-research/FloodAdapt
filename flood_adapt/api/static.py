import os
from pathlib import Path
from typing import Union

import geopandas as gpd
from hydromt_sfincs.quadtree import QuadtreeGrid

from flood_adapt.dbs_classes.database import Database

# upon start up of FloodAdapt


def read_database(database_path: Union[str, os.PathLike], site_name: str) -> Database:
    """Given a path and a site name returns a IDatabase object.

    Parameters
    ----------
    database_path : Union[str, os.PathLike]
        path to database
    site_name : str
        name of the site

    Returns
    -------
    IDatabase
    """
    return Database(database_path, site_name)


def get_aggregation_areas() -> list[gpd.GeoDataFrame]:
    """Get a list of the aggregation areas that are provided in the site configuration.

    These are expected to much the ones in the FIAT model.

    Returns
    -------
    dict[str, GeoDataFrame]
        list of geodataframes with the polygons defining the aggregation areas
    """
    return Database().static.get_aggregation_areas()


def get_obs_points() -> gpd.GeoDataFrame:
    """Get the observation points specified in the site.toml.

    These are also added to the flood hazard model. They are used as marker locations to plot water level time series in the output tab.

    Returns
    -------
    gpd.GeoDataFrame
        gpd.GeoDataFrame with observation points from the site.toml.
    """
    return Database().static.get_obs_points()


def get_model_boundary() -> gpd.GeoDataFrame:
    """Get the model boundary that is used in SFINCS.

    Returns
    -------
    GeoDataFrame
        GeoDataFrame with the model boundary
    """
    return Database().static.get_model_boundary()


def get_model_grid() -> QuadtreeGrid:
    """Get the model grid that is used in SFINCS.

    Returns
    -------
    QuadtreeGrid
        QuadtreeGrid with the model grid
    """
    return Database().static.get_model_grid()


@staticmethod
def get_svi_map() -> Union[gpd.GeoDataFrame, None]:
    """Get the SVI map that are used in Fiat.

    Returns
    -------
    gpd.GeoDataFrame
        gpd.GeoDataFrames with the SVI map, None if not available
    """
    try:
        return Database().static.get_static_map(Database().site.fiat.config.svi.geom)
    except Exception:
        return None


@staticmethod
def get_static_map(path: Union[str, Path]) -> Union[gpd.GeoDataFrame, None]:
    """Get a static map from the database.

    Parameters
    ----------
    path : Union[str, Path]
        path to the static map

    Returns
    -------
    gpd.gpd.GeoDataFrame
        gpd.GeoDataFrame with the static map
    """
    try:
        return Database().static.get_static_map(path)
    except Exception:
        return None


def get_buildings() -> gpd.GeoDataFrame:
    """Get the buildings exposure that are used in Fiat.

    Returns
    -------
    gpd.GeoDataFrame
        gpd.GeoDataFrames with the buildings from FIAT exposure
    """
    return Database().static.get_buildings()


def get_property_types() -> list:
    """Get the property types that are used in the exposure.

    Returns
    -------
    list
        list of property types
    """
    return Database().static.get_property_types()


def get_hazard_measure_types():
    """Get list of all implemented hazard measure types."""
    raise NotImplementedError


def get_impact_measure_types():
    """Get list of all implemented impact measure types."""
    raise NotImplementedError


def get_event_templates():
    """Get list of all implemented event templates."""
    raise NotImplementedError
