from typing import Any

from flood_adapt.object_model.direct_impact.measure.elevate import Elevate
from flood_adapt.object_model.interface.database import IDatabase
from flood_adapt.object_model.interface.measures import IElevate, IMeasure


def get_measures(database: IDatabase) -> dict[str, Any]:
    # sorting and filtering either with PyQt table or in the API
    return database.get_measures()


def get_measure(name: str, database: IDatabase) -> IMeasure:
    return database.get_measure(name)


def create_elevate_measure(attrs: dict[str, Any], database: IDatabase) -> IElevate:
    return Elevate.load_dict(attrs, database.input_path)


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
