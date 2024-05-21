from typing import Any

from flood_adapt.object_model.interface.database import IDatabase
from flood_adapt.object_model.interface.projections import IProjection
from flood_adapt.object_model.object_classes.projection import Projection


def get_projections(database: IDatabase) -> dict[str, Any]:
    # sorting and filtering either with PyQt table or in the API
    return database.projections.list_objects()


def get_projection(name: str, database: IDatabase) -> IProjection:
    return database.projections.get(name)


def create_projection(attrs: dict[str, Any]) -> IProjection:
    return Projection.load_dict(attrs)


def save_projection(projection: IProjection, database: IDatabase) -> None:
    database.projections.save(projection)


def edit_projection(projection: IProjection, database: IDatabase) -> None:
    database.projections.edit(projection)


def delete_projection(name: str, database: IDatabase) -> None:
    database.projections.delete(name)


def copy_projection(
    old_name: str, database: IDatabase, new_name: str, new_description: str
) -> None:
    database.projections.copy(old_name, new_name, new_description)


def get_slr_scn_names(database: IDatabase) -> list:
    return database.get_slr_scn_names()


def interp_slr(database: IDatabase, slr_scenario: str, year: float) -> float:
    return database.interp_slr(slr_scenario, year)


def plot_slr_scenarios(database: IDatabase) -> str:
    return database.plot_slr_scenarios()
