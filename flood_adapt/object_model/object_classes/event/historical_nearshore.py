import os
from datetime import datetime
from pathlib import Path
from typing import Union

import cht_observations.observation_stations as cht_station
import pandas as pd

from flood_adapt.object_model.interface.events import (
    IHistoricalNearshore,
)
from flood_adapt.object_model.io.unitfulvalue import UnitfulLength, UnitTypesLength
from flood_adapt.object_model.models.events import HistoricalNearshoreModel
from flood_adapt.object_model.object_classes.event.event import Event


class HistoricalNearshore(Event, IHistoricalNearshore):
    attrs = HistoricalNearshoreModel
    tide_surge_ts: pd.DataFrame

    @classmethod
    def load_additional_data(cls, filepath: Union[str, os.PathLike]):
        """create Historical Nearshore from toml file"""

        obj = super().load_file(cls, filepath)

        wl_csv_path = Path(Path(filepath).parents[0], obj.attrs.tide.timeseries_file)
        obj.tide_surge_ts = HistoricalNearshore.read_csv(wl_csv_path)
        if obj.attrs.rainfall.source == "timeseries":
            rainfall_csv_path = Path(
                Path(filepath).parents[0], obj.attrs.rainfall.timeseries_file
            )
            obj.rain_ts = HistoricalNearshore.read_csv(rainfall_csv_path)
        if obj.attrs.wind.source == "timeseries":
            wind_csv_path = Path(
                Path(filepath).parents[0], obj.attrs.wind.timeseries_file
            )
            obj.wind_ts = HistoricalNearshore.read_csv(wind_csv_path)

        return obj

    @staticmethod
    def download_wl_data(
        station_id: int,
        start_time_str: str,
        stop_time_str: str,
        units: UnitTypesLength,
        file: Union[str, None],
    ) -> pd.DataFrame:
        """Download waterlevel data from NOAA station using station_id, start and stop time.

        Parameters
        ----------
        station_id : int
            NOAA observation station ID.
        start_time_str : str
            Start time of timeseries in the form of: "YYYMMDD HHMMSS"
        stop_time_str : str
            End time of timeseries in the form of: "YYYMMDD HHMMSS"

        Returns
        -------
        pd.DataFrame
            Dataframe with time as index and waterlevel as first column.
        """
        start_time = datetime.strptime(start_time_str, "%Y%m%d %H%M%S")
        stop_time = datetime.strptime(stop_time_str, "%Y%m%d %H%M%S")
        if file is not None:
            df_temp = HistoricalNearshore.read_csv(file)
            startindex = df_temp.index.get_loc(start_time, method="nearest")
            stopindex = df_temp.index.get_loc(stop_time, method="nearest")
            df = df_temp.iloc[startindex:stopindex, :]
        else:
            # Get NOAA data
            source = cht_station.source("noaa_coops")
            df = source.get_data(station_id, start_time, stop_time)
            df = pd.DataFrame(df)  # Convert series to dataframe
            df = df.rename(columns={"v": 1})
        # convert to gui units
        metric_units = UnitfulLength(value=1.0, units=UnitTypesLength("meters"))
        conversion_factor = metric_units.convert(units)
        df = conversion_factor * df
        return df
