from typing import Any, Union

import flood_adapt.dbs_classes.database as db
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.scenario import Scenario


def get_scenarios() -> dict[str, Any]:
    # sorting and filtering either with PyQt table or in the API
    return db.Database().scenarios.list_objects()


def get_scenario(name: str) -> IScenario:
    return db.Database().scenarios.get(name)


def create_scenario(attrs: dict[str, Any]) -> IScenario:
    return Scenario.load_dict(attrs, db.Database().input_path)


def save_scenario(scenario: IScenario) -> tuple[bool, str]:
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
        db.Database().scenarios.save(scenario)
        return True, ""
    except Exception as e:
        return False, str(e)


def edit_scenario(scenario: IScenario) -> None:
    db.Database().scenarios.edit(scenario)


def delete_scenario(name: str) -> None:
    db.Database().scenarios.delete(name)


def run_scenario(name: Union[str, list[str]]) -> None:
    db.Database().run_scenario(name)
