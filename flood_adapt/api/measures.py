from typing import Any

from flood_adapt.object_model.direct_impact.measure.buyout import Buyout
from flood_adapt.object_model.direct_impact.measure.elevate import Elevate
from flood_adapt.object_model.direct_impact.measure.floodproof import FloodProof
from flood_adapt.object_model.hazard.measure.floodwall import FloodWall
from flood_adapt.object_model.interface.database import IDatabase
from flood_adapt.object_model.interface.measures import (
    IMeasure,
)


def get_measures(database: IDatabase) -> dict[str, Any]:
    return database.get_measures()


def get_measure(name: str, database: IDatabase) -> IMeasure:
    return database.get_measure(name)


def create_measure(attrs: dict[str, Any], type: str, database: IDatabase) -> IMeasure:
    if type == "elevate_properties":
        return Elevate.load_dict(attrs, database.input_path)
    elif type == "buyout_properties":
        return Buyout.load_dict(attrs, database.input_path)
    elif type == "floodproof_properties":
        return FloodProof.load_dict(attrs, database.input_path)
    elif type == "floodwall":
        return FloodWall.load_dict(attrs, database.input_path)


def save_measure(measure: IMeasure, database: IDatabase) -> None:
    database.save_measure(measure)


def edit_measure(measure: IMeasure, database: IDatabase) -> None:
    database.edit_measure(measure)


def delete_measure(name: str, database: IDatabase) -> None:
    database.delete_measure(name)


def copy_measure(
    old_name: str, database: IDatabase, new_name: str, new_long_name: str
) -> None:
    database.copy_measure(old_name, new_name, new_long_name)
