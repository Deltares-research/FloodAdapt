import inspect
import types
from typing import Any

from flood_adapt.object_model.interface.database import IDatabase
from flood_adapt.object_model.interface.strategies import IStrategy
from flood_adapt.object_model.strategy import Strategy


def get_strategies(database: IDatabase) -> dict[str, Any]:
    """Returns a dictionary with info on the strategies that currently exist in the database

    Parameters
    ----------
    database : IDatabase
        Database object

    Returns
    -------
    dict[str, Any]
        Dictionary with info on the strategies
    """
    return database.strategies.list_objects()


def get_strategy(name: str, database: IDatabase) -> IStrategy:
    """Returns the strategy object with the specified name from the database

    Parameters
    ----------
    name : str
        name of the object to be returned
    database : IDatabase
        database object

    Returns
    -------
    IStrategy
        The strategy object with the specified name
    """
    return database.strategies.get(name)


def create_strategy(attrs: dict[str, Any], database: IDatabase) -> IStrategy:
    return Strategy.load_dict(attrs, database.input_path)


def save_strategy(strategy: IStrategy, database: IDatabase) -> None:
    """Save the strategy to the database.

    Parameters
    ----------
    strategy : IStrategy
        The strategy to save.
    database : IDatabase
        The database to save the strategy to.

    Raises
    ------
    ValueError
        Raise error if name is already in use.
    """
    database.strategies.save(strategy)


def delete_strategy(name: str, database: IDatabase) -> None:
    """Deletes an already existing strategy in the database.

    Parameters
    ----------
    name : str
        Name of the strategy to be deleted
    database : IDatabase
        The database to delete the strategy from.

    Raises
    ------
    ValueError
        Raise error if strategy to be deleted is already in use.
    """
    database.strategies.delete(name)


# Get a list of all public functions defined in this module
__all__ = [
    name
    for name, obj in globals().items()
    if (inspect.isfunction(obj) or isinstance(obj, types.FunctionType))
    and not name.startswith("_")
]

# Append 'IMeasure' to the list
__all__.append("IStrategy")
