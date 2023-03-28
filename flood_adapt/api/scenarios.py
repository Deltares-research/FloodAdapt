from typing import Any

from flood_adapt.object_model.interface.database import IDatabase
from flood_adapt.object_model.interface.scenarios import IScenario


def get_scenarios(database: IDatabase) -> dict[str, Any]:
    # sorting and filtering either with PyQt table or in the API
    return database.get_scenarios()

def get_scenario(name: str, database: IDatabase) -> IScenario:
    return database.get_scenario(name)

def delete_scenario(name: str, database: IDatabase) -> None:
    database.delete_scenario(name)




