from enum import Enum
from pathlib import Path
from typing import Optional

import numpy as np
import tomli
from pydantic import BaseModel

from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDirection,
    UnitfulDischarge,
    UnitfulLength,
    UnitfulVelocity,
)


class Mode(str, Enum):
    """class describing the accepted input for the variable mode in Event"""

    single_scenario = "single_scenario"
    risk = "risk"


class Template(str, Enum):
    """class describing the accepted input for the variable template in Event"""

    Synthetic = "Synthetic"
    Hurricane = "Hurricane"


class Timing(str, Enum):
    """class describing the accepted input for the variable timng in Event"""

    historical = "historical"
    idealized = "idealized"


class WindSource(str, Enum):
    track = "track"
    map = "map"
    constant = "constant"
    none = "none"
    timeseries = "timeseries"


class RainfallSource(str, Enum):
    track = "track"
    map = "map"
    constant = "constant"
    none = "none"
    timeseries = "timeseries"
    shape = "shape"


class RiverSource(str, Enum):
    constant = "constant"
    timeseries = "timeseries"
    shape = "shape"


class ShapeType(str, Enum):
    gaussian = "gaussian"
    block = "block"
    triangle = "triangle"


class WindModel(BaseModel):
    source: WindSource
    # constant
    constant_speed: Optional[UnitfulVelocity]
    constant_direction: Optional[UnitfulDirection]
    # timeseries
    wind_timeseries_file: Optional[str]


class RainfallModel(BaseModel):
    source: RainfallSource
    # constant
    constant_intensity: Optional[UnitfulLength]
    # timeseries
    rainfall_timeseries_file: Optional[str]
    # shape
    shape_type: Optional[ShapeType]
    cumulative: Optional[UnitfulLength]
    shape_duration: Optional[float]
    shape_peak_time: Optional[float]
    shape_start_time: Optional[float]
    shape_end_time: Optional[float]


class RiverModel(BaseModel):
    source: RiverSource
    # constant
    constant_discharge: Optional[UnitfulDischarge]
    # shape
    shape_type: Optional[ShapeType]
    base_discharge: Optional[UnitfulDischarge]
    shape_peak: Optional[UnitfulDischarge]
    shape_duration: Optional[float]
    shape_peak_time: Optional[float]
    shape_start_time: Optional[float]
    shape_end_time: Optional[float]


class EventModel(BaseModel):  # add WindModel etc as this is shared among all? templates
    """BaseModel describing the expected variables and data types of attributes common to all event types"""

    name: str
    long_name: str
    mode: Mode
    template: Template
    timing: Timing
    water_level_offset: UnitfulLength
    wind: WindModel
    # rainfall: RainfallModel
    # river: RiverModel


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
    def add_wind_ts(event: EventModel):
        # generating time series of constant wind
        if event.attrs.wind.source == "constant":
            duration = (
                event.attrs.time.duration_before_t0 + event.attrs.time.duration_after_t0
            ) * 3600
            vmag = event.attrs.wind.constant_speed.convert_to_mps() * np.array([1, 1])
            vdir = event.attrs.wind.constant_direction.value * np.array([1, 1])
            time = pd.date_range(
                event.attrs.time.start_time, periods=duration / 600 + 1, freq="600S"
            )
            df = pd.DataFrame.from_dict(
                {"time": time[[0, -1]], "vmag": vmag, "vdir": vdir}
            )
            df = df.set_index("time")
            event.wind_ts = df
            return event
        elif event.attrs.wind.source == "timeseries":
            raise NotImplementedError
        else:
            raise ValueError(
                "A time series can only be generated for wind sources "
                "constant"
                " or "
                "timeseries"
                "."
            )

    @staticmethod
    def add_rainfall_ts(event: EventModel):
        # generating time series of constant wind
        if event.attrs.wind.source == "constant":
            duration = (
                event.attrs.time.duration_before_t0 + event.attrs.time.duration_after_t0
            ) * 3600
            vmag = event.attrs.wind.constant_speed.convert_to_mps() * np.array([1, 1])
            vdir = event.attrs.wind.constant_direction.value * np.array([1, 1])
            time = pd.date_range(
                event.attrs.time.start_time, periods=duration / 600 + 1, freq="600S"
            )
            df = pd.DataFrame.from_dict(
                {"time": time[[0, -1]], "vmag": vmag, "vdir": vdir}
            )
            df = df.set_index("time")
            event.wind_ts = df
            return event
        else:
            raise ValueError(
                "A time series can only be generated for wind sources "
                "constant"
                " or "
                "timeseries"
                "."
            )
