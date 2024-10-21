import os
from datetime import datetime
from pathlib import Path
from typing import Any, Union

import cht_observations.observation_stations as cht_station
import pandas as pd

from flood_adapt.dbs_classes.path_builder import TopLevelDir, db_path
from flood_adapt.object_model.interface.events import (
    HistoricalNearshoreModel,
    IHistoricalNearshore,
)
from flood_adapt.object_model.io.unitfulvalue import UnitfulLength, UnitTypesLength
from flood_adapt.object_model.utils import resolve_filepath, save_file_to_database


class HistoricalNearshore(IHistoricalNearshore):
    rain_ts: pd.DataFrame
    wind_ts: pd.DataFrame
    tide_surge_ts: pd.DataFrame

    def __init__(self, data: dict[str, Any]) -> None:
        """Initialize function called when object is created through the load_file or load_dict methods."""
        if isinstance(data, HistoricalNearshoreModel):
            self.attrs = data
        else:
            self.attrs = HistoricalNearshoreModel.model_validate(data)

        if self.attrs.rainfall.source == "timeseries":
            path = db_path(
                TopLevelDir.input, self.dir_name, self.attrs.rainfall.timeseries_file
            )
            self.rain_ts = HistoricalNearshore.read_csv(path)

        if self.attrs.wind.source == "timeseries":
            path = db_path(
                TopLevelDir.input, self.dir_name, self.attrs.wind.timeseries_file
            )
            self.wind_ts = HistoricalNearshore.read_csv(path)

        if self.attrs.tide.source == "timeseries":
            path = db_path(
                TopLevelDir.input, self.dir_name, self.attrs.tide.timeseries_file
            )
            self.tide_surge_ts = HistoricalNearshore.read_csv(path)

    def save_additional(self, toml_path: Path | str | os.PathLike) -> None:
        if self.attrs.rainfall.source == "timeseries":
            src_path = resolve_filepath(
                self.dir_name, self.attrs.name, self.attrs.rainfall.timeseries_file
            )
            path = save_file_to_database(src_path, Path(toml_path).parent)
            self.attrs.rainfall.timeseries_file = path.name

        if self.attrs.wind.source == "timeseries":
            src_path = resolve_filepath(
                self.dir_name, self.attrs.name, self.attrs.wind.timeseries_file
            )
            path = save_file_to_database(src_path, Path(toml_path).parent)
            self.attrs.wind.timeseries_file = path.name

        for river in self.attrs.river:
            if river.source == "timeseries":
                if river.timeseries_file is None:
                    raise ValueError(
                        "The timeseries file for the river source is not set."
                    )
                src_path = resolve_filepath(
                    self.dir_name, self.attrs.name, river.timeseries_file
                )
                path = save_file_to_database(src_path, Path(toml_path).parent)
                river.timeseries_file = path.name

        if self.attrs.tide.source == "timeseries":
            src_path = resolve_filepath(
                self.dir_name, self.attrs.name, self.attrs.tide.timeseries_file
            )
            path = save_file_to_database(src_path, Path(toml_path).parent)
            self.attrs.tide.timeseries_file = path.name

    @staticmethod
    def download_wl_data(
        station_id: int,
        start_time_str: str,
        stop_time_str: str,
        units: UnitTypesLength,
        source: str,
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
            source_obj = cht_station.source(source)
            df = source_obj.get_data(station_id, start_time, stop_time)
            df = pd.DataFrame(df)  # Convert series to dataframe
            df = df.rename(columns={"v": 1})
        # convert to gui units
        metric_units = UnitfulLength(value=1.0, units=UnitTypesLength("meters"))
        conversion_factor = metric_units.convert(units)
        df = conversion_factor * df
        return df
