from typing import Any

import flood_adapt.dbs_controller as db
from flood_adapt.object_model.interface.strategies import IStrategy
from flood_adapt.object_model.strategy import Strategy


def get_strategies() -> dict[str, Any]:
    # sorting and filtering either with PyQt table or in the API
    return db.Database().strategies.list_objects()


def get_strategy(name: str) -> IStrategy:
    return db.Database().strategies.get(name)


def create_strategy(attrs: dict[str, Any]) -> IStrategy:
    return Strategy.load_dict(attrs, db.Database().input_path)


def save_strategy(strategy: IStrategy) -> None:
    db.Database().strategies.save(strategy)


def delete_strategy(name: str) -> None:
    db.Database().strategies.delete(name)
