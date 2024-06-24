from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
from fiat_toolbox.infographics.infographics_factory import InforgraphicFactory
from fiat_toolbox.metrics_writer.fiat_read_metrics_file import MetricsFileReader

from flood_adapt.dbs_controller import Database


def get_outputs() -> dict[str, Any]:
    # sorting and filtering either with PyQt table or in the API
    return Database().get_outputs()


def get_topobathy_path() -> str:
    return Database().get_topobathy_path()


def get_index_path() -> str:
    return Database().get_index_path()


def get_depth_conversion() -> float:
    return Database().get_depth_conversion()


def get_max_water_level(name: str, rp: int = None) -> np.array:
    return Database().get_max_water_level(name, rp)


def get_fiat_footprints(name: str) -> gpd.GeoDataFrame:
    return Database().get_fiat_footprints(name)


# TODO this does not represent only damages. A more generic name should be used
def get_aggregated_damages(name: str) -> dict[gpd.GeoDataFrame]:
    return Database().get_aggregated_damages(name)


def get_roads(name: str) -> gpd.GeoDataFrame:
    return Database().get_roads(name)


def get_obs_point_timeseries(name: str) -> gpd.GeoDataFrame:
    """Return the HTML strings of the water level timeseries for the given scenario.

    Parameters
    ----------
    name : str
        The name of the scenario.
    database : IDatabase
        The database object.

    Returns
    -------
    str
        The HTML strings of the water level timeseries
    """
    # Get the direct_impacts objects from the scenario
    hazard = Database().scenarios.get(name).direct_impacts.hazard

    # Check if the scenario has run
    if not hazard.has_run_check():
        raise ValueError(
            f"Scenario {name} has not been run. Please run the scenario first."
        )

    output_path = (
        Database()
        .scenarios.get_database_path(get_input_path=False)
        .joinpath(hazard.name)
    )
    gdf = Database().static.get_obs_points()
    gdf["html"] = [
        str(output_path.joinpath("Flooding", f"{station}_timeseries.html"))
        for station in gdf.name
    ]

    return gdf


def get_infographic(name: str) -> str:
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
    database = Database()
    impact = database.scenarios.get(name).direct_impacts

    # Check if the scenario has run
    if not impact.has_run_check():
        raise ValueError(
            f"Scenario {name} has not been run. Please run the scenario first."
        )

    config_path = database.static_path.joinpath("templates", "infographics")
    output_path = database.scenarios.get_database_path(get_input_path=False).joinpath(
        impact.name
    )
    metrics_outputs_path = output_path.joinpath(f"Infometrics_{impact.name}.csv")

    infographic_path = InforgraphicFactory.create_infographic_file_writer(
        infographic_mode=impact.hazard.event_mode,
        scenario_name=impact.name,
        metrics_full_path=metrics_outputs_path,
        config_base_path=config_path,
        output_base_path=output_path,
    ).get_infographics_html()

    return infographic_path


def get_infometrics(name: str) -> pd.DataFrame:
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
    metrics_path = (
        Database()
        .scenarios.get_database_path(get_input_path=False)
        .joinpath(
            name,
            f"Infometrics_{name}.csv",
        )
    )

    # Check if the file exists
    if not metrics_path.exists():
        raise FileNotFoundError(
            f"The metrics file for scenario {name}({str(metrics_path)}) does not exist."
        )

    # Read the metrics file
    return MetricsFileReader(str(metrics_path)).read_metrics_from_file(
        include_long_names=True,
        include_description=True,
        include_metrics_table_selection=True,
    )
