from typing import Any

from flood_adapt.object_model.interface.database import IDatabase
from flood_adapt.object_model.interface.strategies import IStrategy
from flood_adapt.object_model.strategy import Strategy


def get_strategies(database: IDatabase) -> dict[str, Any]:
    # sorting and filtering either with PyQt table or in the API
    return database.get_strategies()


def get_strategy(name: str, database: IDatabase) -> IStrategy:
    return database.get_strategy(name)


def create_strategy(attrs: dict[str, Any], database: IDatabase) -> IStrategy:
    return Strategy.load_dict(attrs, database.input_path)


def save_strategy(strategy: IStrategy, database: IDatabase) -> None:
    database.save_strategy(strategy)


def delete_strategy(name: str, database: IDatabase) -> None:
    database.delete_strategy(name)
