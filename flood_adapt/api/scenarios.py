import inspect
import types
from typing import Any, Union

from flood_adapt.object_model.interface.database import IDatabase
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.scenario import Scenario


def get_scenarios(database: IDatabase) -> dict[str, Any]:
    """Returns a dictionary with info on the scenarios that currently exist in the database
    Parameters
    ----------
    database : IDatabase
        Database object
    Returns
    -------
    dict[str, Any]
        Dictionary with info on the scenarios
    """
    return database.scenarios.list_objects()


def get_scenario(name: str, database: IDatabase) -> IScenario:
    """Returns the scenario object with the specified name from the database
    Parameters
    ----------
    name : str
        name of the object to be returned
    database : IDatabase
        database object
    Returns
    -------
    IScenario
        The scenario object with the specified name
    """
    return database.scenarios.get(name)


def create_scenario(attrs: dict[str, Any], database: IDatabase) -> IScenario:
    return Scenario.load_dict(attrs, database.input_path)


def save_scenario(scenario: IScenario, database: IDatabase) -> (bool, str):
    """Save the scenario to the database.
    Parameters
    ----------
    scenario : IScenario
        The scenario to save.
    database : IDatabase
        The database to save the scenario to.
    Returns
    -------
    bool
        Whether the scenario was saved successfully.
    str
        The error message if the scenario was not saved successfully.
    """
    try:
        database.scenarios.save(scenario)
        return True, ""
    except Exception as e:
        return False, str(e)


def edit_scenario(scenario: IScenario, database: IDatabase) -> None:
    """Edit the scenario in the database.

    Parameters
    ----------
    scenario : IScenario
        The scenario to edit.
    database : IDatabase
        The database to edit the scenario in.

    Raises
    ------
    ValueError
        Raise error if name is already in use.
    """
    database.scenarios.edit(scenario)


def delete_scenario(name: str, database: IDatabase) -> None:
    """Delete the scenario from the database.

    Parameters
    ----------
    name : str
        The name of the scenario to delete.
    database : IDatabase
        The database to delete the scenario from.

    Raises
    ------
    ValueError
        Raise error if object to be deleted is already in use.
    """
    database.scenarios.delete(name)


def run_scenario(name: Union[str, list[str]], database: IDatabase) -> None:
    """Runs a scenario hazard and impacts.

    Parameters
    ----------
    name : Union[str, list[str]]
        name(s) of the scenarios to run.
    database : IDatabase
        Database object

    Raises
    ------
    RuntimeError
        If an error occurs while running one of the scenarios
    """
    database.run_scenario(name)


# Get a list of all public functions defined in this module
__all__ = [
    name
    for name, obj in globals().items()
    if (inspect.isfunction(obj) or isinstance(obj, types.FunctionType))
    and not name.startswith("_")
]

# Append 'IMeasure' to the list
__all__.append("IScenario")
