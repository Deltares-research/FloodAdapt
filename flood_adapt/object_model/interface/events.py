import os
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel

from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDirection,
    UnitfulDischarge,
    UnitfulLength,
    UnitfulVelocity,
)


class Mode(str, Enum):
    """class describing the accepted input for the variable mode in Event"""
    #TODO change to single_event
    single_scenario = "single_scenario"
    risk = "risk"


class Template(str, Enum):
    """class describing the accepted input for the variable template in Event"""

    Synthetic = "Synthetic"
    Hurricane = "Hurricane"
    Historical_nearshore = "Historical_nearshore"
    Historical_offshore = "Historical_offshore"


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
    constant_intensity: Optional[
        float
    ]  # TODO: add units; intensity is in mm/hr or in/hr
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
    shape_peak_time: Optional[float]
    shape_start_time: Optional[float]
    shape_end_time: Optional[float]


class TimeModel(BaseModel):
    """BaseModel describing the expected variables and data types for time parameters of synthetic model"""

    duration_before_t0: Optional[float]
    duration_after_t0: Optional[float]
    start_time: Optional[str] = "20200101 000000"
    end_time: Optional[str] = "20200103 000000"


class TideSource(str, Enum):
    harmonic = "harmonic"
    timeseries = "timeseries"
    model = "model"


class TideModel(BaseModel):
    """BaseModel describing the expected variables and data types for harmonic tide parameters of synthetic model"""

    source: TideSource
    harmonic_amplitude: Optional[UnitfulLength]


class SurgeSource(str, Enum):
    none = "none"
    shape = "shape"


class SurgeModel(BaseModel):
    """BaseModel describing the expected variables and data types for harmonic tide parameters of synthetic model"""

    source: SurgeSource
    shape_type: Optional[str] = "gaussian"
    shape_duration: Optional[float]
    shape_peak_time: Optional[float]
    shape_peak: Optional[UnitfulLength]


class EventModel(BaseModel):  # add WindModel etc as this is shared among all? templates
    """BaseModel describing the expected variables and data types of attributes common to all event types"""

    name: str
    long_name: str
    mode: Mode
    template: Template
    timing: Timing  # TODO: do we need this? We can infer this from template
    water_level_offset: UnitfulLength
    wind: WindModel
    rainfall: RainfallModel
    river: RiverModel
    time: TimeModel
    tide: TideModel
    surge: SurgeModel


class SyntheticModel(EventModel):  # add SurgeModel etc. that fit Synthetic event
    """BaseModel describing the expected variables and data types for parameters of Synthetic that extend the parent class Event"""


class HistoricalNearshoreModel(EventModel):
    """BaseModel describing the expected variables and data types for parameters of HistoricalNearshore that extend the parent class Event"""


class IEvent(ABC):
    attrs: EventModel

    @staticmethod
    @abstractmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """get Event attributes from toml file"""
        ...

    @staticmethod
    @abstractmethod
    def load_dict(data: dict[str, Any]):
        """get Event attributes from an object, e.g. when initialized from GUI"""
        ...

    @abstractmethod
    def save(self, filepath: Union[str, os.PathLike]):
        """save Event attributes to a toml file"""


class ISynthetic(IEvent):
    attrs: SyntheticModel


class IHistoricalNearshore(IEvent):
    attrs: HistoricalNearshoreModel
