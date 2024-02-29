import math
import os
from datetime import datetime, timedelta
from typing import Any, Union

import numpy as np
import pandas as pd
import tomli

from flood_adapt.object_model.hazard.event.event import (
    Event,
)
from flood_adapt.object_model.interface.events import (
    Constants,
    Defaults,
    ShapeType,
    SurgeSource,
    SyntheticEventModel,
)


class Synthetic(Event):
    """class for Synthetic event, can only be initialized from a toml file or dictionar using load_file or load_dict"""

    attrs: SyntheticEventModel
    tide_surge_ts: pd.DataFrame

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """create Synthetic from toml file"""

        obj = Synthetic()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = SyntheticEventModel.parse_obj(toml)

        # synthetic event is the only one without start and stop time, so set this here.
        # Default start time is defined in TimeModel, setting end_time here
        # based on duration before and after T0
        tstart = datetime.strptime(obj.attrs.time.start_time, Defaults._DATETIME_FORMAT)
        end_time = tstart + timedelta(
            hours=obj.attrs.time.duration_before_t0 + obj.attrs.time.duration_after_t0
        )
        obj.attrs.time.end_time = datetime.strftime(end_time, Defaults._DATETIME_FORMAT)
        return obj

    @staticmethod
    def load_dict(data: dict[str, Any]):
        """create Synthetic from object, e.g. when initialized from GUI"""

        obj = Synthetic()
        obj.attrs = SyntheticEventModel.parse_obj(data)
        # synthetic event is the only one without start and stop time, so set this here.
        # Default start time is defined in TimeModel, setting end_time here
        # based on duration before and after T0
        tstart = datetime.strptime(obj.attrs.time.start_time, Defaults._DATETIME_FORMAT)
        end_time = tstart + timedelta(
            hours=obj.attrs.time.duration_before_t0 + obj.attrs.time.duration_after_t0
        )
        obj.attrs.time.end_time = datetime.strftime(end_time, Defaults._DATETIME_FORMAT)
        return obj

    def add_tide_and_surge_ts(self):
        """generating time series of harmoneous tide (cosine) and gaussian surge shape

        Returns
        -------
        self
            updated object with additional attribute of combined tide and surge timeseries as pandas Dataframe
        """
        # time vector
        duration = (
            self.attrs.time.duration_before_t0 + self.attrs.time.duration_after_t0
        ) * Constants._SECONDS_PER_HOUR
        tt = np.arange(0, duration + 1, Defaults._TIMESTEP)

        # tide
        amp = self.attrs.tide.harmonic_amplitude.value
        omega = 2 * math.pi / (Constants._TIDAL_PERIOD / Constants._HOURS_PER_DAY)
        time_shift = (
            float(self.attrs.time.duration_before_t0) * Constants._SECONDS_PER_HOUR
        )
        tide = amp * np.cos(omega * (tt - time_shift) / Constants._SECONDS_PER_DAY)

        # surge
        if self.attrs.surge.source == SurgeSource.SHAPE:
            # surge = self.create_timeseries_from_shape(self.attrs.time, self.attrs.surge)
            time_shift = (
                self.attrs.time.duration_before_t0 + self.attrs.surge.shape_peak_time
            ) * Constants._SECONDS_PER_HOUR
            # convert surge peak to MSL in GUI units
            peak = self.attrs.surge.shape_peak.value
            surge = super().create_timeseries_from_shape(
                ShapeType.GAUSSIAN,
                duration=duration,
                peak=peak,
                shape_duration=self.attrs.surge.shape_duration
                * Constants._SECONDS_PER_HOUR,
                time_shift=time_shift,
            )
        elif self.attrs.surge.source == SurgeSource.NONE:
            surge = np.zeros_like(tt)

        # save to object with pandas daterange
        time = pd.date_range(
            self.attrs.time.start_time,
            periods=duration / Defaults._DEFAULT_TIMESTEP + 1,
            freq=f"{Defaults._DEFAULT_TIMESTEP}S",
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
