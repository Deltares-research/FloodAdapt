import math
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.interface.events import (
    SyntheticModel,
)


class Synthetic(Event):
    """class for Synthetic event, can only be initialized from a toml file or dictionar using load_file or load_dict."""

    attrs: SyntheticModel
    tide_surge_ts: pd.DataFrame

    def __init__(self, data: dict[str, Any]) -> None:
        if isinstance(data, SyntheticModel):
            self.attrs = data
        else:
            self.attrs = SyntheticModel.model_validate(data)
        # synthetic event is the only one without start and stop time, so set this here.
        # Default start time is defined in TimeModel, setting end_time here
        # based on duration before and after T0
        tstart = datetime.strptime(self.attrs.time.start_time, "%Y%m%d %H%M%S")
        end_time = tstart + timedelta(
            hours=self.attrs.time.duration_before_t0 + self.attrs.time.duration_after_t0
        )
        self.attrs.time.end_time = datetime.strftime(end_time, "%Y%m%d %H%M%S")

    def add_tide_and_surge_ts(self):
        """Generate time series of harmoneous tide (cosine) and gaussian surge shape.

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
            peak = self.attrs.surge.shape_peak.value
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
