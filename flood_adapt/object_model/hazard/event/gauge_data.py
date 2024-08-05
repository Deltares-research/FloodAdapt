import os
from pathlib import Path

import cht_observations.observation_stations as cht_station
import pandas as pd
from noaa_coops.station import COOPSAPIError

from flood_adapt.log import FloodAdaptLogging
from flood_adapt.object_model.hazard.interface.models import TimeModel
from flood_adapt.object_model.interface.site import Obs_pointModel, SiteModel
from flood_adapt.object_model.io.unitfulvalue import UnitfulLength, UnitTypesLength

logger = FloodAdaptLogging.getLogger(__name__)


def get_observed_wl_data(
    time: TimeModel,
    site: SiteModel,
    units: UnitTypesLength = UnitTypesLength("meters"),
    source: str = "noaa_coops",
    station_id: int = None,
    out_path: str | os.PathLike = None,
) -> pd.DataFrame:
    """Download waterlevel data from NOAA station using station_id, start and stop time.

    Parameters
    ----------
    time : TimeModel
        Time model with start and end time.
    site : SiteModel
        Site model with observation points.
    units : UnitTypesLength
        Units of the waterlevel data.
    source : str
        Source of the data.
    station_id : int | None
        NOAA observation station ID. If None, all observation stations in the site are downloaded.
    out_path: str | os.PathLike
        Path to store the observed/imported waterlevel data.

    Returns
    -------
    pd.DataFrame
        Dataframe with time as index and the waterlevel for each observation station as columns.
    """
    wl_df = pd.DataFrame()
    if station_id is None:
        station_ids = [obs_point.ID for obs_point in site.obs_point]
    elif isinstance(station_id, int):
        station_ids = [station_id]

    obs_points = [p for p in site.obs_point if p.ID in station_ids]
    if not obs_points:
        logger.warning(f"Could not find observation stations with ID {station_id}.")
        return None

    for obs_point in obs_points:
        if obs_point.file:
            station_data = _read_imported_waterlevels(time=time, path=obs_point.file)
        else:
            station_data = _download_obs_point_data(
                time=time, obs_point=obs_point, source=source
            )
            # Skip if data could not be downloaded
            if station_data is None:
                continue
        station_data = station_data.rename(columns={"waterlevel": obs_point.ID})
        station_data = station_data * UnitfulLength(
            value=1.0, units=UnitTypesLength("meters")
        ).convert(units)

        if wl_df.empty:
            wl_df = station_data
        else:
            wl_df = wl_df.join(station_data, how="outer")

    if out_path is not None:
        wl_df.to_csv(Path(out_path))

    return wl_df


def _download_obs_point_data(
    time: TimeModel, obs_point: Obs_pointModel, source: str = "noaa_coops"
) -> pd.DataFrame | None:
    """Download waterlevel data from NOAA station using station_id, start and stop time.

    Parameters
    ----------
    obs_point : Obs_pointModel
        Observation point model.
    source : str
        Source of the data.

    Returns
    -------
    pd.DataFrame
        Dataframe with time as index and the waterlevel of the observation station as the column.
    None
        If the data could not be downloaded.
    """
    try:
        source_obj = cht_station.source(source)
        df = source_obj.get_data(
            id=obs_point.ID,
            tstart=time.start_time,
            tstop=time.end_time,
        )
        df = pd.DataFrame(df)  # Convert series to dataframe
        df = df.rename(columns={"v": 1})

    except COOPSAPIError as e:
        logger.warning(
            f"Could not download tide gauge data for station {obs_point.ID}. {e}"
        )
        return None
    return df


def _read_imported_waterlevels(time: TimeModel, path: str | os.PathLike):
    """Read waterlevels from an imported csv file.

    Parameters
    ----------
    path : str | os.PathLike
        Path to the csv file.

    Returns
    -------
    pd.DataFrame
        Dataframe with time as index and the waterlevel for each observation station as columns.
    """
    df_temp = pd.read_csv(path, index_col=0, parse_dates=True)
    df_temp.index.names = ["time"]
    startindex = df_temp.index.get_loc(time.start_time, method="nearest")
    stopindex = df_temp.index.get_loc(time.end_time, method="nearest")
    df = df_temp.iloc[startindex:stopindex, :]
    return df
