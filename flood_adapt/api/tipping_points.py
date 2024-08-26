from typing import Any

from flood_adapt.dbs_controller import Database
from flood_adapt.object_model.interface.tipping_points import ITipPoint
from flood_adapt.object_model.tipping_point import TippingPoint


def get_tipping_points() -> dict[str, Any]:
    # sorting and filtering either with PyQt table or in the API
    return Database().tipping_points.list_objects()


def get_tipping_point(name: str) -> ITipPoint:
    return Database().tipping_points.get(name)


def create_tipping_point(attrs: dict[str, Any]) -> ITipPoint:
    return TippingPoint.load_dict(attrs, Database().input_path)


def save_tipping_point(tipping_point: ITipPoint) -> None:
    Database().tipping_points.save(tipping_point)


def edit_tipping_point(tipping_point: ITipPoint) -> None:
    Database().tipping_points.edit(tipping_point)


def delete_tipping_point(name: str) -> None:
    Database().tipping_points.delete(name)


def create_tipping_point_scenarios(name: str) -> None:
    Database().tipping_points.get(name).create_tp_scenarios()


def run_tipping_point(name: str) -> None:
    Database().tipping_points.get(name).run_tp_scenarios()


def plot_tipping_point_results(name: str) -> None:
    Database().tipping_points.get(name).plot_results()
