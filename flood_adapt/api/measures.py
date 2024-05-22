from typing import Any

import geopandas as gpd
import pandas as pd

from flood_adapt.dbs_controller import Database
from flood_adapt.object_model.direct_impact.measure.buyout import Buyout
from flood_adapt.object_model.direct_impact.measure.elevate import Elevate
from flood_adapt.object_model.direct_impact.measure.floodproof import FloodProof
from flood_adapt.object_model.hazard.measure.floodwall import FloodWall
from flood_adapt.object_model.hazard.measure.green_infrastructure import (
    GreenInfrastructure,
)
from flood_adapt.object_model.hazard.measure.pump import Pump
from flood_adapt.object_model.interface.measures import (
    IMeasure,
)
from flood_adapt.object_model.interface.site import ISite


def get_measures() -> dict[str, Any]:
    return Database().measures.list_objects()


def get_measure(name: str) -> IMeasure:
    return Database().measures.get(name)


def create_measure(
    attrs: dict[str, Any], type: str = None
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
    database_path = Database().input_path

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


def save_measure(measure: IMeasure) -> None:
    Database().measures.save(measure)


def edit_measure(measure: IMeasure) -> None:
    Database().measures.edit(measure)


def delete_measure(name: str) -> None:
    Database().measures.delete(name)


def copy_measure(
    old_name: str,  new_name: str, new_description: str
) -> None:
    Database().measures.copy(old_name, new_name, new_description)


# Green infrastructure
def calculate_polygon_area(gdf: gpd.GeoDataFrame, site: ISite) -> float:
    return GreenInfrastructure.calculate_polygon_area(gdf=gdf, site=site)


def calculate_volume(
    area: float, height: float = 0.0, percent_area: float = 100.0
) -> float:
    return GreenInfrastructure.calculate_volume(
        area=area, height=height, percent_area=percent_area
    )


def get_green_infra_table( measure_type: str) -> pd.DataFrame:
    return Database().get_green_infra_table(measure_type)
