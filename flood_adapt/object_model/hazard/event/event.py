from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import tomli

from flood_adapt.object_model.interface.events import (
    EventModel,
    TimeModel,
    WindModel,
)


class Event:
    """abstract parent class for all event types"""

    attrs: EventModel

    @staticmethod
    def generate_timeseries():
        ...

    @staticmethod
    def get_template(filepath: Path):
        """create Synthetic from toml file"""

        obj = Event()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = EventModel.parse_obj(toml)
        return obj.attrs.template

    @staticmethod
    def get_mode(filepath: Path):
        """create Synthetic from toml file"""

        obj = Event()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = EventModel.parse_obj(toml)
        return obj.attrs.mode

    @staticmethod
    def add_wind_ts(time: TimeModel, wind: WindModel) -> pd.DataFrame:
        # generating time series of constant wind
        tstart = datetime.strptime(time.start_time, "%Y%m%d %H%M%S")
        tstop = datetime.strptime(time.end_time, "%Y%m%d %H%M%S")
        duration = (tstop - tstart).seconds()
        if wind.source == "constant":
            vmag = wind.constant_speed.convert_to_mps() * np.array([1, 1])
            vdir = wind.constant_direction.value * np.array([1, 1])
            time_vec = pd.date_range(tstart, periods=duration / 600 + 1, freq="600S")
            df = pd.DataFrame.from_dict(
                {"time": time_vec[[0, -1]], "vmag": vmag, "vdir": vdir}
            )
            df = df.set_index("time")
            return df
        elif wind.source == "timeseries":
            raise NotImplementedError
        else:
            raise ValueError(
                "A time series can only be generated for wind sources "
                "constant"
                " or "
                "timeseries"
                "."
            )
