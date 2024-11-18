from typing import Any

from flood_adapt.dbs_classes.database import Database
from flood_adapt.object_model.interface.projections import IProjection
from flood_adapt.object_model.projection import Projection


def get_projections() -> dict[str, Any]:
    # sorting and filtering either with PyQt table or in the API
    return Database().projections.list_objects()


def get_projection(name: str) -> IProjection:
    return Database().projections.get(name)


def create_projection(attrs: dict[str, Any]) -> IProjection:
    return Projection.load_dict(attrs)


def save_projection(projection: IProjection) -> None:
    Database().projections.save(projection)


def edit_projection(projection: IProjection) -> None:
    Database().projections.edit(projection)


def delete_projection(name: str) -> None:
    Database().projections.delete(name)


def copy_projection(old_name: str, new_name: str, new_description: str) -> None:
    Database().projections.copy(old_name, new_name, new_description)


def get_slr_scn_names() -> list:
    return Database().static.get_slr_scn_names()


def interp_slr(slr_scenario: str, year: float) -> float:
    return Database().interp_slr(slr_scenario, year)


def plot_slr_scenarios() -> str:
    return Database().plot_slr_scenarios()
