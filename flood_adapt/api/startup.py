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


def get_buildings(database: IDatabase) -> GeoDataFrame:
    # TODO should this return a geojson? if yes what form?
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
