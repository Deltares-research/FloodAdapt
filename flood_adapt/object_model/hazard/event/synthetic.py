import math
import os
from typing import Any, Optional, Union

import numpy as np
import pandas as pd
import tomli
import tomli_w
from pydantic import BaseModel

from flood_adapt.object_model.hazard.event.event import Event, EventModel
from flood_adapt.object_model.interface.events import IEvent
from flood_adapt.object_model.io.unitfulvalue import UnitfulLength


class TimeModel(BaseModel):
    """BaseModel describing the expected variables and data types for time parameters of synthetic model"""

    duration_before_t0: float
    duration_after_t0: float
    start_time: Optional[str] = "20200101 000000"
    end_time: Optional[str]


class TideModel(BaseModel):
    """BaseModel describing the expected variables and data types for harmonic tide parameters of synthetic model"""

    source: str
    harmonic_amplitude: UnitfulLength


class SurgeModel(BaseModel):
    """BaseModel describing the expected variables and data types for harmonic tide parameters of synthetic model"""

    source: str
    shape_type: Optional[str] = "gaussian"
    shape_duration: Optional[float]
    shape_peak_time: Optional[float]
    shape_peak: Optional[UnitfulLength]


class SyntheticModel(EventModel):  # add SurgeModel etc. that fit Synthetic event
    """BaseModel describing the expected variables and data types for parameters of Synthetic that extend the parent class Event"""

    time: TimeModel
    tide: TideModel
    surge: SurgeModel


class Synthetic(Event, IEvent):
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
        return obj

    @staticmethod
    def load_dict(data: dict[str, Any]):
        """create Synthetic from object, e.g. when initialized from GUI"""

        obj = Synthetic()
        obj.attrs = SyntheticModel.parse_obj(data)
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
            surge = self.timeseries_shape(self, tt)
        elif self.attrs.surge.source == "none":
            surge = np.zeros_like(tt)

        # save to object with pandas daterange
        time = pd.date_range(
            self.attrs.time.start_time, periods=duration / 600 + 1, freq="600S"
        )
        df = pd.DataFrame.from_dict({"time": time, "0:wl": tide + surge})
        df = df.set_index("time")
        self.tide_surge_ts = df
        return self

    def add_wind_ts(self):
        # generating time series of constant wind
        if self.attrs.wind.source == "constant":
            duration = (
                self.attrs.time.duration_before_t0 + self.attrs.time.duration_after_t0
            ) * 3600
            vmag = self.attrs.wind.constant_speed.convert_to_mps() * np.array([1, 1])
            vdir = self.attrs.wind.constant_direction.value * np.array([1, 1])
            time = pd.date_range(
                self.attrs.time.start_time, periods=duration / 600 + 1, freq="600S"
            )
            df = pd.DataFrame.from_dict(
                {"time": time[[0, -1]], "vmag": vmag, "vdir": vdir}
            )
            df = df.set_index("time")
            self.wind_ts = df
            return self
        else:
            raise ValueError(
                "A time series can only be generated for wind sources "
                "constant"
                " or "
                "timeseries"
                "."
            )

    @staticmethod
    def timeseries_shape(self, tt: np.array) -> np.array:
        """generates 1d vector of shape to generate time series of surge, wind, rain or discharge

        Parameters
        ----------
        tt : np.array
            time vector of floats (starting at zero)

        Returns
        -------
        np.array
            1d array of the shape with the same dimensions as time vector tt
        """

        duration = (
            self.attrs.time.duration_before_t0 + self.attrs.time.duration_after_t0
        ) * 3600
        peak = self.attrs.surge.shape_peak.convert_to_meters()
        if self.attrs.surge.shape_type == "gaussian":
            time_shift = (
                self.attrs.time.duration_before_t0 + self.attrs.surge.shape_peak_time
            ) * 3600
            ts = peak * np.exp(-(((tt - time_shift) / (0.25 * duration)) ** 2))
        elif self.attrs.surge.shape_type == "block":
            ts = np.where((tt > self.attrs.surge.start_shape), peak, 0)
            ts = np.where((tt > self.attrs.surge.end_shape), 0, ts)
        elif self.attrs.surge.shape_type == "triangle":
            time_shift = (
                self.attrs.time.duration_before_t0 + self.attrs.surge.shape_peak_time
            ) * 3600
            tt_interp = [
                self.attrs.surge.start_shape,
                time_shift,
                self.attrs.surge.end_shape,
            ]
            value_interp = [0, peak, 0]
            ts = np.interp(tt, tt_interp, value_interp, left=0, right=0)
        return ts
