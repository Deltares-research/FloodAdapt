from enum import Enum
from pathlib import Path
from typing import Optional

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
    track: "track"
    hindcast_map: "hindcast_map"
    constant: "constant"
    none: "none"
    timeseries: "timeseries"


class RainfallSource(str, Enum):
    track: "track"
    map: "map"
    constant: "constant"
    none: "none"
    timeseries: "timeseries"
    shape: "shape"


class RiverSource(str, Enum):
    constant: "constant"
    timeseries: "timeseries"
    shape: "shape"


class ShapeType(str, Enum):
    gaussian: "gaussian"
    block: "block"
    triangle: "triangle"


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
    shape_duration = Optional[float]
    shape_peak_time = Optional[float]
    shape_start_time = Optional[float]
    shape_end_time = Optional[float]


class RiverModel(BaseModel):
    source: RiverSource
    # constant
    constant_discharge: Optional[UnitfulDischarge]
    # shape
    shape_type: Optional[ShapeType]
    base_discharge: Optional[UnitfulDischarge]
    shape_peak = Optional[UnitfulDischarge]
    shape_duration = Optional[float]
    shape_peak_time = Optional[float]
    shape_start_time = Optional[float]
    shape_end_time = Optional[float]


class EventModel(BaseModel):  # add WindModel etc as this is shared among all? templates
    """BaseModel describing the expected variables and data types of attributes common to all event types"""

    name: str
    long_name: str
    mode: Mode
    template: Template
    timing: Timing
    water_level_offset: UnitfulLength
    wind: WindModel
    rainfall: RainfallModel
    river: RiverModel


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
    
    # def add_wind_ts(self):
    #     # generating time series of constant wind or from file, for historic cases, function is overwritten in Synthetic class
    #     if self.attrs.wind.source == "constant":
    #         float(self.attrs.time.duration_before_t0) * 3600
    #         duration = (
    #             self.attrs.time.duration_before_t0 + self.attrs.time.duration_after_t0
    #         ) * 3600
    #         tt = np.arange(0, duration + 1, 600)
    #         vmag = self.attrs.wind.constant_speed.convert_to_mps * np.ones_like(
    #             tt[0, -1]
    #         )
    #         vdir = self.attrs.wind.constant_direction * np.ones_like(tt[0, -1])
    #         self.wind_ts = pd.DataFrame.from_dict(
    #             {"time": tt[0, -1], "vmag": vmag, "vdir": vdir}
    #         )
    #         return self
    #     elif self.attrs.wind.source == "timeseries":
    #         filepath = Path(
    #             DatabaseIO().events_path,
    #             self.attrs.name,
    #             self.attrs.rainfall.rainfall_timeseries_file,
    #         )
    #         assert filepath.is_file()
    #     else:
    #         raise ValueError(
    #             "A time series can only be generated for wind sources "
    #             "constant"
    #             " or "
    #             "timeseries"
    #             "."
    #         )

