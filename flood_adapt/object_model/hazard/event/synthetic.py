import math
from pathlib import Path

import numpy as np
import pandas as pd
import tomli
import tomli_w
from pydantic import BaseModel

from flood_adapt.object_model.hazard.event.event import Event, EventModel
from flood_adapt.object_model.io.unitfulvalue import UnitfulLength


class TimeModel(BaseModel):
    """BaseModel describing the expected variables and data types for time parameters of synthetic model"""

    duration_before_t0: float
    duration_after_t0: float


class TideModel(BaseModel):
    """BaseModel describing the expected variables and data types for harmonic tide parameters of synthetic model"""

    source: str
    harmonic_amplitude: UnitfulLength


class SyntheticModel(EventModel):  # add SurgeModel etc. that fit Synthetic event
    """BaseModel describing the expected variables and data types for parameters of Synthetic that extend the parent class Event"""

    time: TimeModel
    tide: TideModel


class Synthetic(Event):
    """class for Synthetic event, can only be initialized from a toml file or dictionar using load_file or load_dict"""

    attrs: SyntheticModel
    tide_ts: pd.DataFrame

    @staticmethod
    def load_file(filepath: Path):
        """create Synthetic from toml file"""

        obj = Synthetic()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = SyntheticModel.parse_obj(toml)
        return obj

    @staticmethod
    def load_dict(data: dict):
        """create Synthetic from object, e.g. when initialized from GUI"""

        obj = Synthetic()
        obj.attrs = SyntheticModel.parse_obj(data)
        return obj

    def save(self, file: Path):
        """saving event toml

        Parameters
        ----------
        file : Path
            path to the location where file will be saved
        """
        with open(file, "wb") as f:
            tomli_w.dump(self.attrs.dict(), f)

    def add_tide_ts(self):
        # generating time series of harmoneous tide (cosine)

        amp = self.attrs.tide.harmonic_amplitude.convert_unit()
        omega = 2 * math.pi / (12.4 / 24)
        time_shift = float(self.attrs.time.duration_before_t0) * 3600
        duration = (
            self.attrs.time.duration_before_t0 + self.attrs.time.duration_after_t0
        ) * 3600
        tt = np.arange(0, duration + 1, 600)
        wl = amp * np.cos(omega * (tt - time_shift) / 86400)
        self.tide_ts = pd.DataFrame.from_dict({"time": tt, "wl": wl})
        return self
