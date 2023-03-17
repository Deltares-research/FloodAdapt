from typing import Any

from flood_adapt.object_model.interface.database import IDatabase


def get_scenarios(database: IDatabase) -> dict[str, Any]:
    # sorting and filtering either with PyQt table or in the API
    return database.get_scenarios()
