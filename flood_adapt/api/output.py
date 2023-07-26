from pathlib import Path
from typing import Any

import pandas as pd
from fiat_toolbox.infographics.infographics import InfographicsParser
from fiat_toolbox.metrics_writer.fiat_read_metrics_file import MetricsFileReader

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
    """Make the infographic for the given scenario.
    
    Parameters
    ----------
    name : str
        The name of the scenario.
    database : IDatabase
        The database object.

    Returns
    -------
    str
        The path to the metrics file.
    """

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

def get_infographic(name: str, database: IDatabase) -> str:
    """Return the HTML string of the infographic for the given scenario.
    
    Parameters
    ----------
    name : str
        The name of the scenario.
    database : IDatabase
        The database object.

    Returns
    -------
    str
        The HTML string of the infographic.
    """
    # Get the direct_impacts objects from the scenario
    impact = database.get_scenario(name).direct_impacts

    # Check if the scenario has run
    if not impact.fiat_has_run_check():
        raise ValueError(
            f"Scenario {name} has not been run. Please run the scenario first."
        )

    return InfographicsParser().get_infographics_html(
        scenario_name=name,
        database_path=Path(database.input_path).parent,
    )

def get_infometrics(name: str, database: IDatabase) -> pd.DataFrame:
    """Return the metrics for the given scenario.	

    Parameters
    ----------
    name : str
        The name of the scenario.   
    database : IDatabase
        The database object.

    Returns
    -------
    pd.DataFrame

    Raises
    ------
    FileNotFoundError
        If the metrics file does not exist.
    """
    
    # Create the infographic path
    metrics_path = Path(database.input_path).parent.joinpath(
        "output",
        "infometrics",
        f"{name}_metrics.csv",
    )

    # Check if the file exists
    if not metrics_path.exists():
        raise FileNotFoundError(
            f"The metrics file for scenario {name} does not exist."
        )

    # Read the metrics file
    return MetricsFileReader(str(metrics_path)).read_metrics_from_file(include_long_names=True, include_description=True, include_metrics_table_selection=True)