from typing import Any

import pandas as pd

from flood_adapt.object_model.interface.database import IDatabase
from flood_adapt.object_model.interface.scenarios import IScenario


def get_outputs(database: IDatabase) -> dict[str, Any]:
    # sorting and filtering either with PyQt table or in the API
    return database.get_outputs()


def get_topobathy_path(database: IDatabase) -> str:
    return database.get_topobathy_path()


def get_index_path(database: IDatabase) -> str:
    return database.get_index_path()


def get_max_water_level(name: str, database: IDatabase):
    return database.get_max_water_level(name)


def get_fiat_results(name: str, database: IDatabase):
    return database.get_fiat_results(name)


def get_fiat_footprints(name: str, database: IDatabase):
    return database.get_fiat_footprints(name)


def get_aggregation(name: str, database: IDatabase):
    return database.get_aggregation(name)


def make_infographic(name: str, database: IDatabase) -> str:
    return database.get_scenario(name).infographic()


def get_impact_metrics(scenario: IScenario) -> pd.DataFrame:
    return scenario.impact_metrics()
