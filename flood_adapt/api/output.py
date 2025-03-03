from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
from fiat_toolbox.infographics.infographics_factory import InforgraphicFactory
from fiat_toolbox.metrics_writer.fiat_read_metrics_file import MetricsFileReader

from flood_adapt.dbs_classes.database import Database


def get_outputs() -> dict[str, Any]:
    """Get all completed scenarios from the database.

    Returns
    -------
    dict[str, Any]
        A dictionary containing all scenarios.
        Includes keys: 'name', 'description', 'path', 'last_modification_date', 'objects'
        Each value is a list of the corresponding attribute for each output.
    """
    return Database().get_outputs()


def get_topobathy_path() -> str:
    """
    Return the path of the topobathy tiles in order to create flood maps with water level maps.

    Returns
    -------
    str
        The path to the topobathy file.

    """
    return Database().get_topobathy_path()


def get_index_path() -> str:
    """
    Return the path of the index tiles which are used to connect each water level cell with the topobathy tiles.

    Returns
    -------
    str
        The path to the index file.
    """
    return Database().get_index_path()


def get_depth_conversion() -> float:
    """
    Return the flood depth conversion that is need in the gui to plot the flood map.

    Returns
    -------
    float
        The flood depth conversion.
    """
    return Database().get_depth_conversion()


def get_max_water_level(name: str, rp: int = None) -> np.ndarray:
    """
    Return the maximum water level for the given scenario.

    Parameters
    ----------
    name : str
        The name of the scenario.
    rp : int, optional
        The return period of the water level, by default None

    Returns
    -------
    np.ndarray
        2D gridded map with the maximum waterlevels for each cell.
    """
    return Database().get_max_water_level(name, rp)


def get_building_footprints(name: str) -> gpd.GeoDataFrame:
    """
    Return a geodataframe of the impacts at the footprint level.

    Parameters
    ----------
    name : str
        The name of the scenario.

    Returns
    -------
    gpd.GeoDataFrame
        The impact footprints for the scenario.
    """
    return Database().get_building_footprints(name)


def get_aggregation(name: str) -> dict[str, gpd.GeoDataFrame]:
    """
    Return a dictionary with the aggregated impacts as geodataframes.

    Parameters
    ----------
    name : str
        The name of the scenario.

    Returns
    -------
    dict[str, gpd.GeoDataFrame]
        The aggregated impacts for the scenario.
    """
    return Database().get_aggregation(name)


def get_roads(name: str) -> gpd.GeoDataFrame:
    """
    Return a geodataframe of the impacts at roads.

    Parameters
    ----------
    name : str
        The name of the scenario.

    Returns
    -------
    gpd.GeoDataFrame
        The impacted roads for the scenario.
    """
    return Database().get_roads(name)


def get_obs_point_timeseries(name: str) -> gpd.GeoDataFrame:
    """Return the HTML strings of the water level timeseries for the given scenario.

    Parameters
    ----------
    name : str
        The name of the scenario.

    Returns
    -------
    str
        The HTML strings of the water level timeseries
    """
    db = Database()
    # Get the impacts objects from the scenario
    floodmap = db.scenarios.get_floodmap(name)

    # Check if the scenario has run
    if floodmap is None:
        raise ValueError(
            f"Scenario {name} has not been run. Please run the scenario first."
        )

    output_path = db.scenarios.output_path.joinpath(floodmap.name)
    gdf = db.static.get_obs_points()
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

    Returns
    -------
    str
        The HTML string of the infographic.
    """
    # Get the impacts objects from the scenario
    database = Database()
    flood_map = database.scenarios.get_floodmap(name)

    # Check if the scenario has run
    if flood_map is None:
        raise ValueError(
            f"Scenario {name} has not been run. Please run the scenario first."
        )

    config_path = database.static_path.joinpath("templates", "infographics")
    output_path = database.scenarios.output_path.joinpath(flood_map.name)
    metrics_outputs_path = output_path.joinpath(f"Infometrics_{flood_map.name}.csv")

    infographic_path = InforgraphicFactory.create_infographic_file_writer(
        infographic_mode=flood_map.mode,
        scenario_name=flood_map.name,
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

    Returns
    -------
    pd.DataFrame

    Raises
    ------
    FileNotFoundError
        If the metrics file does not exist.
    """
    # Create the infographic path
    metrics_path = Database().scenarios.output_path.joinpath(
        name,
        f"Infometrics_{name}.csv",
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
