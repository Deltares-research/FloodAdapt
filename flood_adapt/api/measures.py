import inspect
import types
from typing import Any

import geopandas as gpd
import pandas as pd

from flood_adapt.object_model.direct_impact.measure.buyout import Buyout
from flood_adapt.object_model.direct_impact.measure.elevate import Elevate
from flood_adapt.object_model.direct_impact.measure.floodproof import FloodProof
from flood_adapt.object_model.hazard.measure.floodwall import FloodWall
from flood_adapt.object_model.hazard.measure.green_infrastructure import (
    GreenInfrastructure,
)
from flood_adapt.object_model.hazard.measure.pump import Pump
from flood_adapt.object_model.interface.database import IDatabase
from flood_adapt.object_model.interface.measures import (
    IMeasure,
)
from flood_adapt.object_model.interface.site import ISite


def get_measures(database: IDatabase) -> dict[str, Any]:
    """Returns a dictionary with info on the measures that currently
    exist in the database.

    Parameters
    ----------
    database : IDatabase
        Database object

    Returns
    -------
    dict[str, Any]
        Dictionary with info on the measures
    """
    return database.measures.list_objects()


def get_measure(name: str, database: IDatabase) -> IMeasure:
    """Returns a measure object.

    Parameters
    ----------
    name : str
        name of the measure to be returned
    database : IDatabase
        Database object

    Returns
    -------
    IMeasure
        measure object
    """
    return database.measures.get(name)


def create_measure(
    attrs: dict[str, Any], type: str, database: IDatabase = None
) -> IMeasure:
    """Create a measure from a dictionary of attributes and a type string.

    Parameters
    ----------
    attrs : dict[str, Any]
        Dictionary of attributes for the measure.
    type : str
        Type of measure to create.
    database : IDatabase, optional
        Database to use for creating the measure, by default None

    Returns
    -------
    IMeasure
        Measure object.
    """

    # If a database is provided, use it to set the input path for the measure. Otherwise, set it to None.
    database_path = database.input_path if database else None

    if type == "elevate_properties":
        return Elevate.load_dict(attrs, database_path)
    elif type == "buyout_properties":
        return Buyout.load_dict(attrs, database_path)
    elif type == "floodproof_properties":
        return FloodProof.load_dict(attrs, database_path)
    elif type in ["floodwall", "thin_dam", "levee"]:
        return FloodWall.load_dict(attrs, database_path)
    elif type in ["pump", "culvert"]:
        return Pump.load_dict(attrs, database_path)
    elif type in ["water_square", "total_storage", "greening"]:
        return GreenInfrastructure.load_dict(attrs, database_path)


def save_measure(measure: IMeasure, database: IDatabase) -> None:
    """Saves an object in the database. This only saves the toml file. If the object also contains a geojson file,
    this should be saved separately.

    Parameters
    ----------
    measure : IMeasure
        Measure object to be saved in the database
    database : IDatabase
        Database object

    Raises
    ------
    ValueError
        Raise error if name is already in use.
    """
    database.measures.save(measure)


def edit_measure(measure: IMeasure, database: IDatabase) -> None:
    """Edits an already existing measure in the database.

    Parameters
    ----------
    measure : IMeasure
        Measure object to be edited
    database : IDatabase
        Database object

    Raises
    ------
    ValueError
        Raise error if name is already in use.
    """
    database.measures.edit(measure)


def delete_measure(name: str, database: IDatabase) -> None:
    """Deletes an already existing measure in the database.

    Parameters
    ----------
    name : str
        Name of the measure to be deleted
    database : IDatabase
        Database object

    Raises
    ------
    ValueError
        Raise error if object to be deleted is already in use.
    """
    database.measures.delete(name)


def copy_measure(
    old_name: str, database: IDatabase, new_name: str, new_description: str
) -> None:
    """Copies (duplicates) an existing measure, and gives it a new name.

    Parameters
    ----------
    old_name : str
        name of the existing measure
    new_name : str
        name of the new measure
    new_description : str
        description of the new measure
    """
    database.measures.copy(old_name, new_name, new_description)


# Green infrastructure
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
    return GreenInfrastructure.calculate_polygon_area(gdf=gdf, site=site)


def calculate_volume(
    area: float, height: float = 0.0, percent_area: float = 100.0
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
    return GreenInfrastructure.calculate_volume(
        area=area, height=height, percent_area=percent_area
    )


def get_green_infra_table(database: IDatabase, measure_type: str) -> pd.DataFrame:
    """Return a table with different types of green infrastructure measures and their infiltration depths.
    This is read by a csv file in the database.

    Parameters
    ----------
    database : IDatabase
        Database object
    measure_type : str
        Type of measure

    Returns
    -------
    pd.DataFrame
        Table with values
    """
    return database.get_green_infra_table(measure_type)


# Get a list of all public functions defined in this module
__all__ = [
    name
    for name, obj in globals().items()
    if (inspect.isfunction(obj) or isinstance(obj, types.FunctionType))
    and not name.startswith("_")
]

# Append 'IMeasure' to the list
__all__.append("IMeasure")
