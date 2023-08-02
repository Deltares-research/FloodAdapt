from pathlib import Path
from typing import Any

from fiat_toolbox.infographics.infographics import InfographicsParser

from flood_adapt.object_model.interface.database import IDatabase


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
    # Get the direct_impacts objects from the scenario
    impact = database.get_scenario(name).direct_impacts

    # Check if the scenario has run
    if not impact.fiat_has_run_check():
        raise ValueError(
            f"Scenario {name} has not been run. Please run the scenario first."
        )

    return InfographicsParser().write_infographics_to_file(
        scenario_name=name,
        database_path=Path(database.input_path).parent,
        keep_metrics_file=True,
    )
