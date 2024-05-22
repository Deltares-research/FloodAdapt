import os
from pathlib import Path
from typing import Union

from geopandas import GeoDataFrame
from hydromt_sfincs.quadtree import QuadtreeGrid

from flood_adapt.dbs_controller import Database

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


def get_aggregation_areas() -> list[GeoDataFrame]:
    # TODO should this return a list of geojson? if yes what form?
    """Gets the aggregations areas that are used for the site and fiat

    Parameters
    ----------
    database : IDatabase

    Returns
    -------
    list[GeoDataFrame]
        list of GeoDataFrames with the aggregation areas
    """
    return Database().get_aggregation_areas()


def get_obs_points() -> GeoDataFrame:
    """Gets the observation points specified in the site.toml. These are
        also added to the flood hazard model. They are used as marker
        locations to plot water level time series in the output tab.

    Parameters
    ----------
    database : IDatabase

    Returns
    -------
    GeoDataFrame
        GeoDataFrame with observation points from the site.toml.
    """
    return Database().get_obs_points()


def get_model_boundary() -> GeoDataFrame:
    return Database().get_model_boundary()


def get_model_grid() -> QuadtreeGrid:
    """Gets the model grid that is used in SFINCS

    Parameters
    ----------
    database : IDatabase

    Returns
    -------
    QuadtreeGrid
        QuadtreeGrid with the model grid
    """
    return Database().get_model_grid()


@staticmethod
def get_svi_map() -> Union[GeoDataFrame, None]:
    """Gets the SVI map that are used in Fiat

    Parameters
    ----------
    database : IDatabase

    Returns
    -------
    GeoDataFrame
        GeoDataFrames with the SVI map, None if not available
    """
    try:
        return Database().get_static_map(Database().site.attrs.fiat.svi.geom)
    except Exception:
        return None


@staticmethod
def get_static_map(
     path: Union[str, Path]
) -> Union[GeoDataFrame, None]:
    """Gets a static map from the database

    Parameters
    ----------
    database : IDatabase
        database object
    path : Union[str, Path]
        path to the static map

    Returns
    -------
    gpd.GeoDataFrame
        GeoDataFrame with the static map
    """
    try:
        return Database().get_static_map(path)
    except Exception:
        return None


def get_buildings() -> GeoDataFrame:
    """Gets the buildings exposure that are used in Fiat

    Parameters
    ----------
    database : IDatabase

    Returns
    -------
    GeoDataFrame
        GeoDataFrames with the buildings from FIAT exposure
    """
    return Database().get_buildings()


def get_property_types() -> list:
    return Database().get_property_types()


def get_hazard_measure_types():
    raise NotImplementedError


def get_impact_measure_types():
    raise NotImplementedError


def get_event_templates():
    # get a list ideally automatically from the child classes of the parent class Event
    raise NotImplementedError
