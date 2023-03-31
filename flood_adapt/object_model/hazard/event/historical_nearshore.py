import os
from datetime import datetime
from typing import Any, Union

import pandas as pd
import tomli
import tomli_w

from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.interface.events import (
    HistoricalNearshoreModel,
    IEvent,
)


class HistoricalNearshore(Event, IEvent):

    attrs = HistoricalNearshoreModel
    tide_surge_ts: pd.DataFrame
    start_time: datetime
    end_time: datetime

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """create Synthetic from toml file"""

        obj = HistoricalNearshore()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = HistoricalNearshoreModel.parse_obj(toml)

        return obj
    
    @staticmethod
    def load_dict(data: dict[str, Any]):
        """create Synthetic from object, e.g. when initialized from GUI"""

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

    def add_wl_from_csv(self):
        """Create dataframe from csv file"""
        df = pd.read_csv(self.attrs.water_level.csv_path,names=[0,1]) #TODO: make general; now tailored for specific csv 
        df[0] = [datetime.strptime(time, "%Y-%m-%d %H:%M:%S") for time in df[0]] #Make datetime object
        self.start_time = df[0][0]
        self.end_time = df[0][len(df[0])-1]
        df[0] = [(time - df[0][0]).total_seconds() for time in df[0]] #Make time relative to start time in seconds
        self.tide_surge_ts = df
        return self
    