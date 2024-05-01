import inspect
import types
from typing import Any

from flood_adapt.object_model.interface.database import IDatabase
from flood_adapt.object_model.interface.projections import IProjection
from flood_adapt.object_model.projection import Projection


def get_projections(database: IDatabase) -> dict[str, Any]:
    """Returns a dictionary with info on the projections that currently
    exist in the database

    Parameters
    ----------
    database : IDatabase
        Database object

    Returns
    -------
    dict[str, Any]
        Dictionary with info on the projections
    """
    return database.projections.list_objects()


def get_projection(name: str, database: IDatabase) -> IProjection:
    """Returns the projection object with the specified name from the database

    Parameters
    ----------
    name : str
        name of the object to be returned
    database : IDatabase
        database object

    Returns
    -------
    IProjection
        The projection object with the specified name
    """
    return database.projections.get(name)


def create_projection(attrs: dict[str, Any]) -> IProjection:
    """Create Projection from a dictionary

    Parameters
    ----------
    attrs : dict[str, Any]
        Dictionary of attributes for the projection.

    Returns
    -------
    IProjection
        Projection object
    """
    return Projection.load_dict(attrs)


def save_projection(projection: IProjection, database: IDatabase) -> None:
    """Save the projection to the database.

    Parameters
    ----------
    projection : IProjection
        The projection to save.
    database : IDatabase
        The database to save the projection to.

    Raises
    ------
    Exception
        If the projection could not be saved.
    """
    database.projections.save(projection)


def edit_projection(projection: IProjection, database: IDatabase) -> None:
    """Edits an already existing projection object in the database.

    Parameters
    ----------
    projection : IProjection
        The projection to edit.
    database : IDatabase
        The database to save the projection to.

    Raises
    ------
    ValueError
        Raise error if name is already in use.
    """
    database.projections.edit(projection)


def delete_projection(name: str, database: IDatabase) -> None:
    """Deletes an already existing projection object in the database.

    Parameters
    ----------
    name : str
        name of the projection to be deleted
    database : IDatabase
        database object

    Raises
    ------
    ValueError
        Raise error if projection to be deleted is already in use.
    """
    database.projections.delete(name)


def copy_projection(
    old_name: str, database: IDatabase, new_name: str, new_description: str
) -> None:
    """Copies (duplicates) an existing projection, and gives it a new name.

    Parameters
    ----------
    old_name : str
        name of the existing projection
    database : IDatabase
        database object
    new_name : str
        name of the new projection
    new_description : str
        description of the new projection
    """
    database.projections.copy(old_name, new_name, new_description)


def get_slr_scn_names(database: IDatabase) -> list:
    return database.get_slr_scn_names()


def interp_slr(database: IDatabase, slr_scenario: str, year: float) -> float:
    """interpolating SLR value and referencing it to the SLR reference year from the site toml

    Parameters
    ----------
    slr_scenario : str
        SLR scenario name from the coulmn names in static\slr\slr.csv
    year : float
        year to evaluate

    Returns
    -------
    float
        _description_

    Raises
    ------
    ValueError
        if the reference year is outside of the time range in the slr.csv file
    ValueError
        if the year to evaluate is outside of the time range in the slr.csv file
    """
    return database.interp_slr(slr_scenario, year)


def plot_slr_scenarios(database: IDatabase) -> str:
    return database.plot_slr_scenarios()


# Get a list of all public functions defined in this module
__all__ = [
    name
    for name, obj in globals().items()
    if (inspect.isfunction(obj) or isinstance(obj, types.FunctionType))
    and not name.startswith("_")
]

# Append 'IMeasure' to the list
__all__.append("IProjection")
