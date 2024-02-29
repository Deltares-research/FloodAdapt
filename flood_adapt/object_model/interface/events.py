import os
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

from pydantic import BaseModel, model_validator

from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDirection,
    UnitfulDischarge,
    UnitfulIntensity,
    UnitfulLength,
    UnitfulVelocity,
    UnitTypesLength,
)


# move to toml file
class Constants(Any, Enum):
    """class describing the accepted input for the variable constants in Event"""

    _TIDAL_PERIOD = 12.4
    _HOURS_PER_DAY = 24
    _SECONDS_PER_DAY = 86400
    _SECONDS_PER_HOUR = 3600


# move to toml file
class Defaults(Any, Enum):
    _DATETIME_FORMAT = "%Y%m%d %H%M%S"
    _START_TIME = "20200101 000000"
    _END_TIME = "20200103 000000"
    _TIMESTEP = 600


# Enums
class Mode(str, Enum):
    """class describing the accepted input for the variable mode in Event"""

    SINGLE_EVENT = "single_event"
    RISK = "risk"


class Template(str, Enum):
    """class describing the accepted input for the variable template in Event"""

    SYNTHETIC = "synthetic"
    NEARSHORE = "nearshore"
    OFFSHORE = "offshore"
    HISTORICAL = "historical"
    HURRICANE = "hurricane"


class ShapeType(str, Enum):
    GAUSSIAN = "gaussian"
    BLOCK = "block"
    TRIANGLE = "triangle"
    SCS = "scs"


class WindSource(str, Enum):
    TRACK = "track"
    MAP = "map"
    CONSTANT = "constant"
    NONE = "none"  # TODO remove?
    TIMESERIES = "timeseries"


# Validated
class WindModel(BaseModel):
    source: WindSource
    constant_speed: Optional[float] = None
    constant_direction: Optional[float] = None
    timeseries_file: Optional[str] = None

    @model_validator(mode="after")
    def validate_windModel(self):
        if self.source == WindSource.TIMESERIES:
            if self.timeseries_file is None:
                raise ValueError(
                    "Timeseries file must be set when source is timeseries"
                )
        elif self.source == WindSource.CONSTANT:
            if self.constant_speed is None:
                raise ValueError("Constant speed must be set when source is constant")
            elif self.constant_speed < 0:
                raise ValueError("Constant speed must be positive")

            elif self.constant_direction is None:
                raise ValueError(
                    "Constant direction must be set when source is constant"
                )
            elif self.constant_direction < 0 or self.constant_direction > 360:
                raise ValueError("Constant direction must be between 0 and 360")
        return self


class RainfallSource(str, Enum):
    TRACK = "track"
    MAP = "map"
    CONSTANT = "constant"
    NONE = "none"  # TODO remove?
    TIMESERIES = "timeseries"
    SHAPE = "shape"


# Validated
class RainfallModel(BaseModel):
    source: RainfallSource
    increase: Optional[float] = 0.0
    # constant
    constant_intensity: Optional[UnitfulIntensity] = None
    # timeseries
    timeseries_file: Optional[str] = None
    # shape
    shape_type: Optional[ShapeType] = None
    cumulative: Optional[UnitfulLength] = None
    shape_peak_intensity: Optional[float] = None
    shape_start_time: Optional[float] = None
    shape_end_time: Optional[float] = None

    @model_validator(mode="after")
    def validate_rainfallModel(self):

        if self.source != RainfallSource.NONE:
            if self.increase is None:
                raise ValueError("Increase must be set when source is not none")
            if self.increase < 0:
                raise ValueError("Increase must be positive")

        if self.source == RainfallSource.CONSTANT:
            if self.constant_intensity is None:
                raise ValueError(
                    "Constant intensity must be set when source is constant"
                )
        elif self.source == RainfallSource.TIMESERIES:
            if self.timeseries_file is None:
                raise ValueError(
                    "Timeseries file must be set when source is timeseries"
                )

        elif self.source == RainfallSource.SHAPE:
            if self.shape_type is None:
                raise ValueError("Shape type must be set when source is shape")
            elif self.cumulative is None:
                raise ValueError("Cumulative must be set when source is shape")
            elif self.shape_peak_intensity is None:
                raise ValueError(
                    "Shape peak intensity must be set when source is shape"
                )
            elif self.shape_start_time is None:
                raise ValueError("Shape start time must be set when source is shape")
            elif self.shape_end_time is None:
                raise ValueError("Shape end time must be set when source is shape")
        return self


class RiverSource(str, Enum):
    CONSTANT = "constant"
    TIMESERIES = "timeseries"
    SHAPE = "shape"


# Validated
class RiverModel(BaseModel):
    source: RiverSource

    # constant
    constant_discharge: Optional[UnitfulDischarge] = None

    # timeseries
    timeseries_file: Optional[str] = None

    # shape
    shape_type: Optional[ShapeType] = None
    base_discharge: Optional[UnitfulDischarge] = None
    shape_peak: Optional[UnitfulDischarge] = None
    shape_duration: Optional[float] = None
    shape_peak_time: Optional[float] = None
    shape_start_time: Optional[float] = None
    shape_end_time: Optional[float] = None

    @model_validator(mode="after")
    def validate_riverModel(self):
        if self.source == RiverSource.CONSTANT:
            if self.constant_discharge is None:
                raise ValueError(
                    "Constant discharge must be set when source is constant"
                )
            elif self.constant_discharge.value < 0:
                raise ValueError("Constant discharge must be positive")

        elif self.source == RiverSource.TIMESERIES:
            if self.timeseries_file is None:
                raise ValueError(
                    "Timeseries file must be set when source is timeseries"
                )
            elif Path(self.timeseries_file).suffix != ".csv":
                raise ValueError("Timeseries file must be a .csv file")
            elif not Path(self.timeseries_file).is_file():
                raise ValueError("Timeseries file must be a valid file")

        elif self.source == RiverSource.SHAPE:
            if self.shape_type is None:
                raise ValueError("Shape type must be set when source is shape")

            elif self.base_discharge is None:
                raise ValueError("Base discharge must be set when source is shape")
            elif self.base_discharge < 0:
                raise ValueError("Base discharge must be positive")

            elif self.shape_peak is None:
                raise ValueError("Shape peak must be set when source is shape")
            elif self.shape_peak < 0:
                raise ValueError("Shape peak must be positive")

            elif self.shape_duration is None:
                raise ValueError("Shape duration must be set when source is shape")
            elif self.shape_duration < 0:
                raise ValueError("Shape duration must be positive")

            elif self.shape_peak_time is None:
                raise ValueError("Shape peak time must be set when source is shape")
            elif self.shape_peak_time < 0:
                raise ValueError("Shape peak time must be positive")

            elif self.shape_start_time is None:
                raise ValueError("Shape start time must be set when source is shape")
            elif self.shape_end_time is None:
                raise ValueError("Shape end time must be set when source is shape")
            elif self.shape_start_time >= self.shape_end_time:
                raise ValueError("Shape start time must be less than shape end time")
        return self


class Timing(str, Enum):
    """class describing the accepted input for the variable timng in Event"""

    HISTORICAL = "historical"
    IDEALIZED = "idealized"


# Validated
class TimeModel(BaseModel):
    """BaseModel describing the expected variables and data types for time parameters of synthetic model"""

    duration_before_t0: float
    duration_after_t0: float
    start_time: Optional[str] = Defaults._DEFAULT_START_TIME
    end_time: Optional[str] = Defaults._DEFAULT_END_TIME

    @model_validator(mode="after")
    def validate_timeModel(self):
        if self.duration_before_t0 < 0:
            raise ValueError("Duration before T0 must be positive")
        elif self.duration_after_t0 < 0:
            raise ValueError("Duration after T0 must be positive")

        elif datetime.datetime.strptime(
            self.start_time, Defaults._DATETIME_FORMAT
        ) > datetime.datetime.strptime(self.end_time, Defaults._DATETIME_FORMAT):
            raise ValueError("Start time must be before end time")

        return self


class TideSource(str, Enum):
    HARMONIC = "harmonic"
    TIMESERIES = "timeseries"
    MODEL = "model"


# Validated
class TideModel(BaseModel):
    """BaseModel describing the expected variables and data types for harmonic tide parameters of synthetic model"""

    source: TideSource
    harmonic_amplitude: Optional[UnitfulLength] = None
    timeseries_file: Optional[str] = None

    @model_validator(mode="after")
    def validate_tideModel(self):
        if self.source == TideSource.HARMONIC:
            if self.harmonic_amplitude is None:
                raise ValueError(
                    "Harmonic amplitude must be set when source is harmonic"
                )
            elif self.harmonic_amplitude.value < 0:
                raise ValueError("Harmonic amplitude must be positive")

        elif self.source == TideSource.TIMESERIES:
            if self.timeseries_file is None:
                raise ValueError(
                    "Timeseries file must be set when source is timeseries"
                )
            elif Path(self.timeseries_file).suffix != ".csv":
                raise ValueError("Timeseries file must be a .csv file")
            elif not Path(self.timeseries_file).is_file():
                raise ValueError("Timeseries file must be a valid file")
        return self


class SurgeSource(str, Enum):
    NONE = "none"  # TODO remove?
    SHAPE = "shape"


# Validated
class SurgeModel(BaseModel):
    """BaseModel describing the expected variables and data types for harmonic tide parameters of synthetic model"""

    source: SurgeSource
    shape_type: Optional[str] = ShapeType.GAUSSIAN
    shape_duration: Optional[float] = None
    shape_peak_time: Optional[float] = None
    shape_peak: Optional[UnitfulLength] = None

    @model_validator(mode="after")
    def validate_surgeModel(self):
        if self.source == SurgeSource.SHAPE:
            if self.shape_type is None:
                raise ValueError("Shape type must be set when source is shape")
            elif self.shape_duration is None:
                raise ValueError("Shape duration must be set when source is shape")
            elif self.shape_peak_time is None:
                raise ValueError("Shape peak time must be set when source is shape")
            elif self.shape_peak is None:
                raise ValueError("Shape peak must be set when source is shape")
        return self


class TranslationModel(BaseModel):
    """BaseModel describing the expected variables and data types for translation parameters of hurricane model"""

    eastwest_translation: UnitfulLength = UnitfulLength(
        value=0.0, units=UnitTypesLength.meters
    )

    northsouth_translation: UnitfulLength = UnitfulLength(
        value=0.0, units=UnitTypesLength.meters
    )


class OverlandModel(BaseModel):
    """BaseModel describing the expected variables and data types for overland parameters of a model"""

    wind: WindModel
    river: RiverModel
    tide: TideModel
    surge: SurgeModel
    rainfall: Optional[RainfallModel]


class OffShoreModel(BaseModel):
    wind: WindModel
    rainfall: RainfallModel
    tide: TideModel


class HurricaneModel(BaseModel):
    track_name: str
    hurricane_translation: TranslationModel


class EventModel(BaseModel):
    """BaseModel describing all variables and data types of attributes common to all event types"""

    # Every event
    template: Template  # -> validate the optional models that a template requires
    mode: Mode  # -> validate the optional models that a mode requires
    timing: Timing  # -> validate the optional models that a timing requires
    name: str
    description: Optional[str] = ""

    # Optional parameters used by all Event child classes
    overland: Optional[OverlandModel] = None
    offshore: Optional[OffShoreModel] = None

    # Optional parameters used by some Event child classes
    time: Optional[TimeModel] = None
    water_level_offset: Optional[UnitfulLength] = None  # validate positive?
    wind: Optional[WindModel] = None
    rainfall: Optional[RainfallModel] = None
    river: Optional[list[RiverModel]] = None
    tide: Optional[TideModel] = None
    surge: Optional[SurgeModel] = None
    hurricane: Optional[HurricaneModel] = None


# TODO investigate
class EventSetModel(BaseModel):
    """BaseModel describing the expected variables and data types of attributes common to a risk event that describes the probabilistic event set"""

    # add WindModel etc as this is shared among all? templates
    # TODO validate
    name: str
    mode: Mode
    description: Optional[str] = ""
    subevent_name: Optional[list[str]] = []
    frequency: Optional[list[float]] = []


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
        ...


#### SYNTHETIC ####
class SyntheticEventModel(EventModel):
    """BaseModel describing the expected variables and data types for parameters of Synthetic that extend the parent class Event"""

    template: Template = Template.SYNTHETIC
    timing: Timing = Timing.IDEALIZED

    @model_validator(mode="after")
    def validate_syntheticEventModel(self):
        if self.template != Template.SYNTHETIC:
            raise ValueError("Template for a Synthetic event must be synthetic")
        elif self.timing != Timing.IDEALIZED:
            raise ValueError("Timing for a Synthetic event must be idealized")
        return self


#### HISTORICAL #### should be read-only
class HistoricalEventModel(EventModel):
    """BaseModel describing the expected variables and data types for parameters of Historical that extend the parent class Event"""

    template: Template = Template.HISTORICAL
    timing: Timing = Timing.HISTORICAL

    @model_validator(mode="after")
    def validate_historicalEventModel(self):
        if self.template != Template.HISTORICAL:
            raise ValueError("Template for a Historical event must be historical")
        elif self.timing != Timing.HISTORICAL:
            raise ValueError("Historical events must have historical timing")
        return self


#### NEARSHORE ####
class NearShoreEventModel(EventModel):
    """BaseModel describing the expected variables and data types for parameters of HistoricalNearshore that extend the parent class Event"""

    template: Template = Template.HISTORICAL

    @model_validator(mode="after")
    def validate_nearshoreEventModel(self):
        if self.template != Template.HISTORICAL:
            raise ValueError("Template for a Nearshore event must be historical")
        return self


#### OFFSHORE ####
class OffShoreEventModel(EventModel):
    """BaseModel describing the expected variables and data types for parameters of HistoricalOffshore that extend the parent class Event"""

    template: Template = Template.OFFSHORE

    @model_validator(mode="after")
    def validate_nearshoreEventModel(self):
        if self.template != Template.OFFSHORE:
            raise ValueError("Template for a Nearshore event must be offshore")
        return self


# Move to offshore_event.py
# class OffshoreEvent(Event):
#     attrs: OffShoreEventModel


#### HURRICANE ####
class HurricaneEventModel(EventModel):
    """BaseModel describing the expected variables and data types for parameters of HistoricalHurricane that extend the parent class Event"""

    template: Template = Template.HURRICANE
    timing: Timing = Timing.HISTORICAL
    hurricane_translation: TranslationModel
    track_name: str

    @model_validator(mode="after")
    def validate_hurricaneEventModel(self):
        if self.template != Template.HURRICANE:
            raise ValueError("Template for a Hurricane event must be hurricane")
        elif self.timing != Timing.HISTORICAL:
            raise ValueError("Hurricane events must have historical timing")
        return self


# Move to hurricane_event.py
# class HurricaneEvent(Event):
#     attrs: HurricaneEventModel
