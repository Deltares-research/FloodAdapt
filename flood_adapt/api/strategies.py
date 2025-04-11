from typing import Any

from flood_adapt.dbs_classes.database import Database
from flood_adapt.object_model.interface.strategies import Strategy


def get_strategies() -> dict[str, Any]:
    """
    Get all strategies from the database.

    Returns
    -------
    dict[str, Any]
        A dictionary containing all strategies.
        Includes keys: 'name', 'description', 'path', 'last_modification_date', 'objects'
        Each value is a list of the corresponding attribute for each strategy.
    """
    return Database().strategies.list_objects()


def get_strategy(name: str) -> Strategy:
    """
    Get a strategy from the database by name.

    Parameters
    ----------
    name : str
        The name of the strategy to retrieve.

    Returns
    -------
    Strategy
        The strategy object with the given name.

    Raises
    ------
    ValueError
        If the strategy with the given name does not exist.
    """
    return Database().strategies.get(name)


def create_strategy(attrs: dict[str, Any]) -> Strategy:
    """Create a new strategy object.

    Parameters
    ----------
    attrs : dict[str, Any]
        The attributes of the strategy object to create. Should adhere to the Strategy schema.

    Returns
    -------
    Strategy
        The strategy object

    Raises
    ------
    ValueError
        If the strategy with the given name does not exist.
        If attrs does not adhere to the Strategy schema.
    """
    return Strategy(**attrs)


def save_strategy(strategy: Strategy) -> None:
    """
    Save a strategy object to the database.

    Parameters
    ----------
    strategy : Strategy
        The strategy object to save.

    Raises
    ------
    ValueError
        If the strategy object is not valid.
        If the strategy object already exists.
    """
    Database().strategies.save(strategy)


def delete_strategy(name: str) -> None:
    """
    Delete a strategy from the database.

    Parameters
    ----------
    name : str
        The name of the strategy to delete.

    Raises
    ------
    ValueError
        If the strategy does not exist.
    """
    Database().strategies.delete(name)
