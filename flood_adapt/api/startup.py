import os
from typing import Union

from geopandas import GeoDataFrame

from flood_adapt.dbs_controller import Database
from flood_adapt.object_model.interface.database import IDatabase

# upon start up of FloodAdapt


def read_database(database_path: Union[str, os.PathLike], site_name: str) -> IDatabase:
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


def get_aggregation_areas(database: IDatabase) -> list[GeoDataFrame]:
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
    return database.get_aggregation_areas()


def get_obs_points(database: IDatabase) -> GeoDataFrame:
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
    return database.get_obs_points()


def get_model_boundary(database: IDatabase) -> GeoDataFrame:
    return database.get_model_boundary()


def get_svi_map(database: IDatabase) -> GeoDataFrame:
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
        return database.get_static_map(database.site.attrs.fiat.svi.geom)
    except Exception:
        return None

def get_buildings(database: IDatabase) -> GeoDataFrame:
    """Gets the buildings exposure that are used in Fiat

    Parameters
    ----------
    database : IDatabase

    Returns
    -------
    GeoDataFrame
        GeoDataFrames with the buildings from FIAT exposure
    """
    return database.get_buildings()


def get_property_types(database: IDatabase) -> list:
    return database.get_property_types()


def get_hazard_measure_types():
    raise NotImplementedError


def get_impact_measure_types():
    raise NotImplementedError


def get_event_templates():
    # get a list ideally automatically from the child classes of the parent class Event
    raise NotImplementedError
