from typing import Any

import geopandas as gpd
import pandas as pd

from flood_adapt.dbs_classes.database import Database
from flood_adapt.object_model.hazard.measure.floodwall import FloodWall
from flood_adapt.object_model.hazard.measure.green_infrastructure import (
    GreenInfrastructure,
)
from flood_adapt.object_model.hazard.measure.pump import Pump
from flood_adapt.object_model.impact.measure.buyout import Buyout
from flood_adapt.object_model.impact.measure.elevate import Elevate
from flood_adapt.object_model.impact.measure.floodproof import FloodProof
from flood_adapt.object_model.interface.config.site import Site
from flood_adapt.object_model.interface.measures import (
    IMeasure,
    MeasureModel,
    MeasureType,
    SelectionType,
)
from flood_adapt.object_model.io import unit_system as us

__all__ = [
    "get_measures",
    "get_measure",
    "create_measure",
    "save_measure",
    "edit_measure",
    "delete_measure",
    "copy_measure",
    "calculate_polygon_area",
    "calculate_volume",
    "get_green_infra_table",
    "MeasureType",
    "MeasureModel",
    "SelectionType",
]


def get_measures() -> dict[str, Any]:
    """
    Get all measures from the database.

    Returns
    -------
    dict[str, Any]
        A dictionary containing all measures.
        Includes keys: 'name', 'description', 'path', 'last_modification_date', 'objects'
        Each value is a list of the corresponding attribute for each measure.
    """
    return Database().measures.list_objects()


def get_measure(name: str) -> IMeasure:
    """
    Get a measure from the database by name.

    Parameters
    ----------
    name : str
        The name of the measure to retrieve.

    Returns
    -------
    IMeasure
        The measure object with the given name.

    Raises
    ------
    ValueError
        If the measure with the given name does not exist.
    """
    return Database().measures.get(name)


def create_measure(attrs: dict[str, Any], type: str = None) -> IMeasure:
    """Create a measure from a dictionary of attributes and a type string.

    Parameters
    ----------
    attrs : dict[str, Any]
        Dictionary of attributes for the measure.
    type : str
        Type of measure to create.

    Returns
    -------
    IMeasure
        Measure object.
    """
    if type == "elevate_properties":
        return Elevate.load_dict(attrs)
    elif type == "buyout_properties":
        return Buyout.load_dict(attrs)
    elif type == "floodproof_properties":
        return FloodProof.load_dict(attrs)
    elif type in ["floodwall", "thin_dam", "levee"]:
        return FloodWall.load_dict(attrs)
    elif type in ["pump", "culvert"]:
        return Pump.load_dict(attrs)
    elif type in ["water_square", "total_storage", "greening"]:
        return GreenInfrastructure.load_dict(attrs)
    else:
        raise ValueError(f"Invalid measure type: {type}")


def save_measure(measure: IMeasure) -> None:
    """Save an event object to the database.

    Parameters
    ----------
    measure : IMeasure
        The measure object to save.


    Raises
    ------
    ValueError
        If the event object is not valid.
    """
    Database().measures.save(measure)


def edit_measure(measure: IMeasure) -> None:
    """Edit an event object in the database.

    Parameters
    ----------
    measure : IMeasure
        The measure object to edit.


    Raises
    ------
    ValueError
        If the event object does not exist.
    """
    Database().measures.edit(measure)


def delete_measure(name: str) -> None:
    """Delete an event from the database.

    Parameters
    ----------
    name : str
        The name of the event to delete.

    Raises
    ------
    ValueError
        If the event does not exist.
    """
    Database().measures.delete(name)


def copy_measure(old_name: str, new_name: str, new_description: str) -> None:
    """Copy an event in the database.

    Parameters
    ----------
    old_name : str
        The name of the event to copy.
    new_name : str
        The name of the new event.
    new_description : str
        The description of the new event
    """
    Database().measures.copy(old_name, new_name, new_description)


def calculate_polygon_area(gdf: gpd.GeoDataFrame, site: Site) -> float:
    """
    Calculate the area of a polygon from a GeoDataFrame.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        A GeoDataFrame containing the polygon geometry.
    site : ISite
        An instance of ISite representing the site information.

    Returns
    -------
        float: The area of the polygon in the specified units.
    """
    return GreenInfrastructure.calculate_polygon_area(gdf=gdf, site=site)


def calculate_volume(
    area: us.UnitfulArea,
    height: us.UnitfulHeight = us.UnitfulHeight(
        value=0.0, units=us.UnitTypesLength.meters
    ),
    percent_area: float = 100.0,
) -> float:
    """
    Calculate the volume of green infrastructure based on the given area, height, and percent area.

    Parameters
    ----------
    area : float
        The area of the green infrastructure in square units.
    height : float
        The height of the green infrastructure in units. Defaults to 0.0.
    percent_area : float
        The percentage of the area to be considered. Defaults to 100.0.


    Returns
    -------
        float: The calculated volume of the green infrastructure.
    """
    return GreenInfrastructure.calculate_volume(
        area=area, height=height, percent_area=percent_area
    )


def get_green_infra_table(measure_type: str) -> pd.DataFrame:
    """Return a table with different types of green infrastructure measures and their infiltration depths.

    Parameters
    ----------
    measure_type : str
        The type of green infrastructure measure.

    Returns
    -------
    pd.DataFrame
        A table with different types of green infrastructure measures and their infiltration depths.

    """
    return Database().static.get_green_infra_table(measure_type)
