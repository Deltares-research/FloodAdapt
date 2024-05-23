from typing import Any, Union

from flood_adapt.dbs_controller import Database
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.scenario import Scenario


def get_scenarios() -> dict[str, Any]:
    # sorting and filtering either with PyQt table or in the API
    return Database().scenarios.list_objects()


def get_scenario(name: str) -> IScenario:
    return Database().scenarios.get(name)


def create_scenario(attrs: dict[str, Any]) -> IScenario:
    return Scenario.load_dict(attrs, Database().input_path)


def save_scenario(scenario: IScenario) -> (bool, str):
    """Save the scenario to the Database().
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
        Database().scenarios.save(scenario)
        return True, ""
    except Exception as e:
        return False, str(e)


def edit_scenario(scenario: IScenario) -> None:
    Database().scenarios.edit(scenario)


def delete_scenario(name: str) -> None:
    Database().scenarios.delete(name)


def run_scenario(name: Union[str, list[str]]) -> None:
    Database().run_scenario(name)
