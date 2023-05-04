import os
from datetime import datetime
from pathlib import Path
from typing import Any, Union

import pandas as pd
import tomli
import tomli_w

from flood_adapt.object_model.hazard.event.cht_scripts.station_source import (
    StationSource,
)
from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.interface.events import (
    HistoricalNearshoreModel,
    IHistoricalNearshore,
)


class HistoricalNearshore(Event, IHistoricalNearshore):
    attrs = HistoricalNearshoreModel
    tide_surge_ts: pd.DataFrame

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """create Synthetic from toml file"""

        obj = HistoricalNearshore()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = HistoricalNearshoreModel.parse_obj(toml)

        csv_path = Path(Path(filepath).parents[0], "tide.csv")
        obj.tide_surge_ts = HistoricalNearshore.read_wl_csv(csv_path)

        return obj

    @staticmethod
    def load_dict(data: dict[str, Any]):
        """create Historical Nearshore from object, e.g. when initialized from GUI"""

        obj = HistoricalNearshore()
        obj.attrs = HistoricalNearshoreModel.parse_obj(data)
        return obj

    def save(self, filepath: Union[str, os.PathLike]):
        """Saving event toml

        Parameters
        ----------
        file : Path
            path to the location where file will be saved
        """
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)

    @staticmethod
    def read_wl_csv(csvpath: Union[str, os.PathLike]):
        df = pd.read_csv(csvpath, index_col=0, names=[1])
        df.index.names = ["time"]
        df.index = pd.to_datetime(df.index)
        # Save as attribute of HistoricalNearshore class
        return df

    @staticmethod
    def download_wl_data(station_id, start_time_str, stop_time_str):
        start_time = datetime.strptime(start_time_str, "%Y%m%d %H%M%S")
        stop_time = datetime.strptime(stop_time_str, "%Y%m%d %H%M%S")
        # Get NOAA data
        source = StationSource.source("noaa_coops")
        df = source.get_data(station_id, start_time, stop_time)
        return df
