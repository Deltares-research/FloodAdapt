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

        # synthtic event is the only one wthout start and stop time, so set this here.
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
        # synthtic event is the only one wthout start and stop time, so set this here.
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
        ) * 3600
        tt = np.arange(0, duration + 1, 600)

        # tide
        amp = self.attrs.tide.harmonic_amplitude.convert_to_meters()
        omega = 2 * math.pi / (12.4 / 24)
        time_shift = float(self.attrs.time.duration_before_t0) * 3600
        tide = amp * np.cos(omega * (tt - time_shift) / 86400)

        # surge
        if self.attrs.surge.source == "shape":
            # surge = self.timeseries_shape(self.attrs.time, self.attrs.surge)
            time_shift = (
                self.attrs.time.duration_before_t0 + self.attrs.surge.shape_peak_time
            ) * 3600
            surge = self.timeseries_shape(
                "gaussian",
                duration,
                self.attrs.surge.shape_peak.convert_to_meters(),
                shape_duration=duration,
                time_shift=time_shift,
            )
        elif self.attrs.surge.source == "none":
            surge = np.zeros_like(tt)

        # save to object with pandas daterange
        time = pd.date_range(
            self.attrs.time.start_time, periods=duration / 600 + 1, freq="600S"
        )
        df = pd.DataFrame.from_dict({"time": time, 1: tide + surge})
        df = df.set_index("time")
        self.tide_surge_ts = df
        return self

    def add_dis_ts(self):
        """adds discharge timeseries to event object

        Returns
        -------
        self
            updated object with wind timeseries added in pf.DataFrame format
        """
        # generating time series of constant discahrge
        # TODO: add for loop to handle multiple rivers
        if self.attrs.river.source == "constant":
            df = super().generate_dis_ts(self.attrs.time, self.attrs.river)
            self.dis_ts = df
            return self
        elif self.attrs.river.source == "shape":
            duration = (
                self.attrs.time.duration_before_t0 + self.attrs.time.duration_after_t0
            ) * 3600
            time_shift = (
                self.attrs.time.duration_before_t0 + self.attrs.river.shape_peak_time
            ) * 3600
            start_shape = (
                self.attrs.time.duration_before_t0
                + self.attrs.river.shape_peak_time
                + self.attrs.river.shape_start_time
            ) * 3600
            end_shape = (
                self.attrs.time.duration_before_t0
                + self.attrs.river.shape_peak_time
                + self.attrs.river.shape_end_time
            ) * 3600
            # subtract base discharge from peak
            river = self.timeseries_shape(
                self.attrs.river.shape_type,
                duration,
                self.attrs.river.shape_peak.convert_to_cms()-self.attrs.river.base_discharge.convert_to_cms(),
                time_shift=time_shift,
                start_shape=start_shape,
                end_shape=end_shape,
            )
            # add base discharge to timeseries
            river += self.attrs.river.base_discharge.convert_to_cms()
            # save to object with pandas daterange
            time = pd.date_range(
                self.attrs.time.start_time, periods=duration / 600 + 1, freq="600S"
            )
            df = pd.DataFrame.from_dict({"time": time, 1: river})
            df = df.set_index("time")
            self.dis_ts = df
            return self

    def add_wind_ts(self):
        """adds wind it timeseries to event object

        Returns
        -------
        self
            updated object with wind timeseries added in pf.DataFrame format
        """
        # generating time series of constant wind
        if self.attrs.wind.source == "constant":
            df = super().generate_wind_ts(self.attrs.time, self.attrs.wind)
            self.wind_ts = df
            return self

    @staticmethod
    def timeseries_shape(
        shape_type: str, duration: float, peak: float, **kwargs
    ) -> np.ndarray:
        time_shift = kwargs.get("time_shift", None)
        start_shape = kwargs.get("start_shape", None)
        end_shape = kwargs.get("end_shape", None)
        shape_duration = kwargs.get("shape_duration", None)
        tt = np.arange(0, duration + 1, 600)
        if shape_type == "gaussian":
            ts = peak * np.exp(-(((tt - time_shift) / (0.25 * shape_duration)) ** 2))
        elif shape_type == "block":
            ts = np.where((tt > start_shape), peak, 0)
            ts = np.where((tt > end_shape), 0, ts)
        elif shape_type == "triangle":
            tt_interp = [
                start_shape,
                time_shift,
                end_shape,
            ]
            value_interp = [0, peak, 0]
            ts = np.interp(tt, tt_interp, value_interp, left=0, right=0)
        return ts
