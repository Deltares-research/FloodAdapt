from typing import Any

from flood_adapt.dbs_classes.database import Database
from flood_adapt.object_model.interface.projections import Projection


def get_projections() -> dict[str, Any]:
    """
    Get all projections from the database.

    Returns
    -------
    dict[str, Any]
        A dictionary containing all projections.
        Includes keys: 'name', 'description', 'path', 'last_modification_date', 'objects'
        Each value is a list of the corresponding attribute for each projection.
    """
    return Database().projections.list_objects()


def get_projection(name: str) -> Projection:
    """Get a projection from the database by name.

    Parameters
    ----------
    name : str
        The name of the projection to retrieve.

    Returns
    -------
    Projection
        The projection object with the given name.

    Raises
    ------
    ValueError
        If the projection with the given name does not exist.
    """
    return Database().projections.get(name)


def create_projection(attrs: dict[str, Any]) -> Projection:
    """Create a new projection object.

    Parameters
    ----------
    attrs : dict[str, Any]
        The attributes of the projection object to create. Should adhere to the Projection schema.

    Returns
    -------
    Projection
        The projection object created from the attributes.

    Raises
    ------
    ValueError
        If the attributes do not adhere to the Projection schema.
    """
    return Projection(**attrs)


def save_projection(projection: Projection) -> None:
    """Save a projection object to the database.

    Parameters
    ----------
    projection : Projection
        The projection object to save.

    Raises
    ------
    ValueError
        If the projection object is not valid.
    """
    Database().projections.save(projection)


def edit_projection(projection: Projection) -> None:
    """Edit a projection object in the database.

    Parameters
    ----------
    projection : Projection
        The projection object to edit.

    Raises
    ------
    ValueError
        If the projection object does not exist.
    """
    Database().projections.edit(projection)


def delete_projection(name: str) -> None:
    """Delete a projection from the database.

    Parameters
    ----------
    name : str
        The name of the projection to delete.

    Raises
    ------
    ValueError
        If the projection does not exist.
        If the projection is used in a scenario.
    """
    Database().projections.delete(name)


def copy_projection(old_name: str, new_name: str, new_description: str) -> None:
    """Copy a projection in the database.

    Parameters
    ----------
    old_name : str
        The name of the projection to copy.
    new_name : str
        The name of the new projection.
    new_description : str
        The description of the new projection
    """
    Database().projections.copy(old_name, new_name, new_description)


def get_slr_scn_names() -> list:
    """
    Get all sea level rise scenario names from the database.

    Returns
    -------
    list
        List of scenario names
    """
    return Database().static.get_slr_scn_names()


def interp_slr(slr_scenario: str, year: float) -> float:
    """
    Interpolate sea level rise for a given scenario and year.

    Parameters
    ----------
    slr_scenario : str
        The name of the sea level rise scenario.
    year : float
        The year to interpolate sea level rise for.

    Returns
    -------
    float
        The interpolated sea level rise for the given scenario and year.
    """
    return Database().interp_slr(slr_scenario, year)


def plot_slr_scenarios() -> str:
    """
    Plot sea level rise scenarios.

    Returns
    -------
    str
        The path to the html plot of the sea level rise scenarios.
    """
    return Database().plot_slr_scenarios()
