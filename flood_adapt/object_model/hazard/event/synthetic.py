import math
import os
from datetime import datetime, timedelta
from typing import Any, Union

import numpy as np
import pandas as pd
import tomli
import tomli_w

from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.interface.events import (
    ISynthetic,
    SyntheticModel,
)


class Synthetic(Event, ISynthetic):
    """class for Synthetic event, can only be initialized from a toml file or dictionar using load_file or load_dict"""

    attrs: SyntheticModel
    tide_surge_ts: pd.DataFrame

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """create Synthetic from toml file"""

        obj = Synthetic()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = SyntheticModel.parse_obj(toml)

        # synthetic event is the only one without start and stop time, so set this here.
        # Default start time is defined in TimeModel, setting end_time here
        # based on duration before and after T0
        tstart = datetime.strptime(obj.attrs.time.start_time, "%Y%m%d %H%M%S")
        end_time = tstart + timedelta(
            hours=obj.attrs.time.duration_before_t0 + obj.attrs.time.duration_after_t0
        )
        obj.attrs.time.end_time = datetime.strftime(end_time, "%Y%m%d %H%M%S")
        return obj

    @staticmethod
    def load_dict(data: dict[str, Any]):
        """create Synthetic from object, e.g. when initialized from GUI"""

        obj = Synthetic()
        obj.attrs = SyntheticModel.parse_obj(data)
        # synthetic event is the only one without start and stop time, so set this here.
        # Default start time is defined in TimeModel, setting end_time here
        # based on duration before and after T0
        tstart = datetime.strptime(obj.attrs.time.start_time, "%Y%m%d %H%M%S")
        end_time = tstart + timedelta(
            hours=obj.attrs.time.duration_before_t0 + obj.attrs.time.duration_after_t0
        )
        obj.attrs.time.end_time = datetime.strftime(end_time, "%Y%m%d %H%M%S")
        return obj

    def save(self, filepath: Union[str, os.PathLike]):
        """saving event toml

        Parameters
        ----------
        file : Path
            path to the location where file will be saved
        """
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)

    def add_tide_and_surge_ts(self, msl):
        """generating time series of harmoneous tide (cosine) and gaussian surge shape

        Returns
        -------
        self
            updated object with additional attribute of combined tide and surge timeseries as pandas Dataframe
        """
        # time vector
        duration = (
            self.attrs.time.duration_before_t0 + self.attrs.time.duration_after_t0
        ) * 3600
        tt = np.arange(0, duration + 1, 600)

        # tide
        amp = self.attrs.tide.harmonic_amplitude.value
        omega = 2 * math.pi / (12.4 / 24)
        time_shift = float(self.attrs.time.duration_before_t0) * 3600
        tide = amp * np.cos(omega * (tt - time_shift) / 86400)

        # surge
        if self.attrs.surge.source == "shape":
            # surge = self.timeseries_shape(self.attrs.time, self.attrs.surge)
            time_shift = (
                self.attrs.time.duration_before_t0 + self.attrs.surge.shape_peak_time
            ) * 3600
            # convert surge peak to MSL in GUI units
            peak = self.attrs.surge.shape_peak.value - msl
            surge = super().timeseries_shape(
                "gaussian",
                duration=duration,
                peak=peak,
                shape_duration=self.attrs.surge.shape_duration * 3600,
                time_shift=time_shift,
            )
        elif self.attrs.surge.source == "none":
            surge = np.zeros_like(tt)

        # save to object with pandas daterange
        time = pd.date_range(
            self.attrs.time.start_time, periods=duration / 600 + 1, freq="600S"
        )
        # add tide, surge and difference between water level reference from site toml and MSL
        df = pd.DataFrame.from_dict(
            {
                "time": time,
                1: tide + surge,
            }
        )
        df = df.set_index("time")
        self.tide_surge_ts = df
        return self
