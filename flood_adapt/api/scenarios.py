from typing import Any, Union

from flood_adapt.dbs_classes.database import Database
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.scenario import Scenario


def get_scenarios() -> dict[str, Any]:
    """Get all scenarios from the database.

    Returns
    -------
    dict[str, Any]
        A dictionary containing all scenarios.
        Includes keys: 'name', 'description', 'path', 'last_modification_date', 'objects'.
        Each value is a list of the corresponding attribute for each scenario.
    """
    return Database().scenarios.list_objects()


def get_scenario(name: str) -> IScenario:
    """Get a scenario from the database by name.

    Parameters
    ----------
    name : str
        The name of the scenario to retrieve.

    Returns
    -------
    IScenario
        The scenario object with the given name.

    Raises
    ------
    ValueError
        If the scenario with the given name does not exist.
    """
    return Database().scenarios.get(name)


def create_scenario(attrs: dict[str, Any]) -> IScenario:
    """Create a new scenario object.

    Parameters
    ----------
    attrs : dict[str, Any]
        The attributes of the scenario object to create. Should adhere to the ScenarioModel schema.

    Returns
    -------
    IScenario
        The scenario object created from the attributes.

    Raises
    ------
    ValueError
        If the attributes do not adhere to the ScenarioModel schema.
    """
    return Scenario.load_dict(attrs)


def save_scenario(scenario: IScenario) -> tuple[bool, str]:
    """Save the scenario to the database.

    Parameters
    ----------
    scenario : IScenario
        The scenario to save.

    Returns
    -------
    bool
        Whether the scenario was saved successfully.
    str
        The error message if the scenario was not saved successfully.
    """
    try:
        Database().scenarios.save(scenario)
        return True, ""
    except Exception as e:
        return False, str(e)


def edit_scenario(scenario: IScenario) -> None:
    """Edit a scenario object in the database.

    Parameters
    ----------
    scenario : IScenario
        The scenario object to edit.

    Raises
    ------
    ValueError
        If the scenario object does not exist.
    """
    Database().scenarios.edit(scenario)


def delete_scenario(name: str) -> None:
    """Delete a scenario from the database.

    Parameters
    ----------
    name : str
        The name of the scenario to delete.

    Raises
    ------
    ValueError
        If the scenario does not exist.
    """
    Database().scenarios.delete(name)


def run_scenario(name: Union[str, list[str]]) -> None:
    """Run a scenario.

    Parameters
    ----------
    name : Union[str, list[str]]
        The name(s) of the scenario to run.

    Raises
    ------
    ValueError
        If the scenario does not exist.
    """
    Database().run_scenario(name)
