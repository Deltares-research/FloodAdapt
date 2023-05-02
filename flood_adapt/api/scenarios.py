from typing import Any

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


def save_scenario(scenario: IScenario, database: IDatabase) -> None:
    database.save_scenario(scenario)


def edit_scenario(scenario: IScenario, database: IDatabase) -> None:
    database.edit_scenario(scenario)


def delete_scenario(name: str, database: IDatabase) -> None:
    database.delete_scenario(name)


def run_hazard_models(scenario: IScenario) -> None:
    scenario.run_hazard_models()
