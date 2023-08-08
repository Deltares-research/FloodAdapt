from typing import Any, Union

from flood_adapt.object_model.interface.database import IDatabase
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.scenario import Scenario


def get_scenarios(database: IDatabase) -> dict[str, Any]:
    # sorting and filtering either with PyQt table or in the API
    return database.get_scenarios()


def get_scenario(name: str, database: IDatabase) -> IScenario:
    return database.get_scenario(name)


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
        database.save_scenario(scenario)
        return True, ""
    except Exception as e:
        return False, str(e)


def edit_scenario(scenario: IScenario, database: IDatabase) -> None:
    database.edit_scenario(scenario)


def delete_scenario(name: str, database: IDatabase) -> None:
    database.delete_scenario(name)


def run_scenario(name: Union[str, list[str]], database: IDatabase) -> None:
    database.run_scenario(name)
