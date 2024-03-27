import os
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

from pydantic import BaseModel, field_validator, model_validator

from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDirection,
    UnitfulDischarge,
    UnitfulIntensity,
    UnitfulLength,
    UnitfulTime,
    UnitfulVelocity,
    UnitfulVolume,
    UnitTypesDischarge,
    UnitTypesLength,
    UnitTypesTime,
)


# move to toml file
class Constants(Enum):
    """class describing the accepted input for the variable constants in Event"""

    _TIDAL_PERIOD = 12.4
    _HOURS_PER_DAY = 24
    _SECONDS_PER_DAY = 86400
    _SECONDS_PER_HOUR = 3600


# move to toml file
class DefaultsStr(str, Enum):
    _DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    _START_TIME = "2020-01-01 00:00:00"
    _END_TIME = "2020-01-03 00:00:00"


class DefaultsInt(Enum):
    _TIMESTEP = UnitfulTime(600, UnitTypesTime.seconds)


# Enums
class Mode(str, Enum):
    """class describing the accepted input for the variable mode in Event"""

    single_event = "single_event"
    risk = "risk"


class Template(str, Enum):
    """class describing the accepted input for the variable template in Event"""

    synthetic = "synthetic"
    nearshore = "nearshore"
    offshore = "offshore"
    historical = "historical"
    hurricane = "hurricane"


class ShapeType(str, Enum):
    gaussian = "gaussian"
    constant = "constant"
    triangle = "triangle"
    scs = "scs"
    csv_file = "csv_file"
    harmonic = "harmonic"


class WindSource(str, Enum):
    timeseries = "timeseries"
    none = "none"
    track = "track"
    map = "map"
    constant = "constant"


class Scstype(str, Enum):
    type1 = "type1"
    type1a = "type1a"
    type2 = "type2"
    type3 = "type3"


class TimeseriesModel(BaseModel):
    # Required
    shape_type: ShapeType
    start_time: UnitfulTime
    end_time: UnitfulTime

    # Either one of these must be set
    peak_intensity: Optional[
        Union[UnitfulIntensity, UnitfulDischarge, UnitfulLength]
    ] = None
    cumulative: Optional[Union[UnitfulLength, UnitfulVolume]] = None

    # Only required for ShapeType.scs or ShapeType.csv_file
    csv_file_path: Optional[Union[str, Path]] = None
    scstype: Optional[Scstype] = None

    @field_validator("csv_file_path")
    @classmethod
    def validate_file_path(cls, value):
        if value is not None:
            if Path(value).suffix != ".csv":
                raise ValueError("Timeseries file must be a .csv file")
            elif not Path(value).is_file():
                raise ValueError("Timeseries file must be a valid file")
        return value

    @model_validator(mode="after")
    def validate_timeseries_model_start_end_time(self):
        if self.start_time > self.end_time:
            raise ValueError(
                f"Timeseries start time cannot be later than its end time: {self.start_time}, {self.end_time}"
            )
        return self

    @model_validator(mode="after")
    def validate_timeseries_model_optional_variables(self):
        if self.shape_type == ShapeType.scs:
            if (
                self.csv_file_path is None
                or self.scstype is None
                or self.cumulative is None
            ):
                raise ValueError(
                    f"csvfile, scstype and cumulative must be provided for SCS timeseries: {self.csv_file_path}, {self.scstype}, {self.cumulative}"
                )

        elif self.shape_type == ShapeType.csv_file:
            if self.csv_file_path is None:
                raise ValueError("csvfile must be provided for csv_file timeseries")

        else:
            if self.cumulative is not None and self.peak_intensity is not None:
                raise ValueError(
                    "Exactly one of peak_intensity or cumulative must be set"
                )

            if self.cumulative is None and self.peak_intensity is None:
                raise ValueError(
                    "Exactly one of peak_intensity or cumulative must be set"
                )

        return self


class WindModel(BaseModel):
    source: WindSource
    constant_speed: Optional[UnitfulVelocity] = None
    constant_direction: Optional[UnitfulDirection] = None
    timeseries_file: Optional[Union[str, Path]] = None

    @model_validator(mode="after")
    def validate_windModel(self):
        if self.source == WindSource.timeseries:
            if self.timeseries_file is None:
                raise ValueError(
                    "Timeseries file must be set when source is timeseries"
                )
            elif Path(self.timeseries_file).suffix != ".csv":
                raise ValueError("Timeseries file must be a .csv file")
            elif not Path(self.timeseries_file).is_file():
                raise ValueError("Timeseries file must be a valid file")

        elif self.source == WindSource.constant:
            if self.constant_speed is None:
                raise ValueError("Constant speed must be set when source is constant")
            elif self.constant_direction is None:
                raise ValueError(
                    "Constant direction must be set when source is constant"
                )
        return self


class RainfallSource(str, Enum):
    none = "none"
    timeseries = "timeseries"
    track = "track"
    map = "map"


class RainfallModel(BaseModel):
    source: RainfallSource
    increase: float = 0.0  # in %
    timeseries: Optional[TimeseriesModel] = None

    @field_validator("increase")
    @classmethod
    def validate_increase(cls, value):
        if value < 0:
            raise ValueError("Increase must be positive")
        return value

    @model_validator(mode="after")
    def validate_rainfallModel(self):
        if self.source == RainfallSource.timeseries:
            if self.timeseries is None:
                raise ValueError(
                    "TimeseriesModel must be set when source is timeseries"
                )
        return self


class RiverDischargeModel(BaseModel):
    timeseries: TimeseriesModel
    base_discharge: UnitfulDischarge = UnitfulDischarge(0, UnitTypesDischarge.cms)


class Timing(str, Enum):
    """class describing the accepted input for the variable timng in Event"""

    historical = "historical"
    idealized = "idealized"


class TimeModel(BaseModel):
    """BaseModel describing the expected variables and data types for time parameters of synthetic model"""

    timing: Timing
    duration_before_t0: UnitfulTime
    duration_after_t0: UnitfulTime
    start_time: Optional[str] = DefaultsStr._START_TIME
    end_time: Optional[str] = DefaultsStr._END_TIME

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time_format(cls, value):
        try:
            datetime.strptime(value, DefaultsStr._DATETIME_FORMAT.value)
        except ValueError:
            raise ValueError(
                f"Time must be in format {DefaultsStr._DATETIME_FORMAT.value}. Got {value}"
            )
        return value

    @model_validator(mode="after")
    def validate_timeModel(self):
        if self.duration_before_t0.value < 0:
            raise ValueError("Duration before T0 must be positive")
        elif self.duration_after_t0.value < 0:
            raise ValueError("Duration after T0 must be positive")
        elif datetime.strptime(
            self.start_time, DefaultsStr._DATETIME_FORMAT.value
        ) > datetime.strptime(self.end_time, DefaultsStr._DATETIME_FORMAT.value):
            raise ValueError("Start time must be before end time")

        return self


class TideSource(str, Enum):
    timeseries = "timeseries"
    model = "model"


class TideModel(BaseModel):
    """BaseModel describing the expected variables and data types for harmonic tide parameters of synthetic model"""

    source: TideSource
    timeseries: Optional[TimeseriesModel] = None

    @model_validator(mode="after")
    def validate_tideModel(self):
        if self.source == TideSource.timeseries:
            if self.timeseries is None:
                raise ValueError(
                    "Timeseries Model must be set when source is timeseries"
                )
        return self


class SurgeSource(str, Enum):
    none = "none"
    timeseries = "timeseries"


class SurgeModel(BaseModel):
    """BaseModel describing the expected variables and data types for harmonic tide parameters of synthetic model"""

    source: SurgeSource
    timeseries: Optional[TimeseriesModel] = None

    @model_validator(mode="after")
    def validate_surgeModel(self):
        if self.source == SurgeSource.timeseries:
            if self.timeseries is None:
                raise ValueError(
                    "Timeseries Model must be set when source is timeseries"
                )
        return self


class TranslationModel(BaseModel):
    """BaseModel describing the expected variables and data types for translation parameters of hurricane model"""

    eastwest_translation: UnitfulLength = UnitfulLength(
        value=0.0, units=UnitTypesLength.meters
    )

    northsouth_translation: UnitfulLength = UnitfulLength(
        value=0.0, units=UnitTypesLength.meters
    )


class HurricaneModel(BaseModel):  # TODO add validator?
    track_name: str
    hurricane_translation: TranslationModel


class OverlandModel(BaseModel):
    """BaseModel describing the expected variables and data types for overland parameters of a model"""

    wind: Optional[WindModel] = None
    river: Optional[list[RiverDischargeModel]] = None
    tide: Optional[TideModel] = None
    surge: Optional[SurgeModel] = None
    rainfall: Optional[RainfallModel] = None
    hurricane: Optional[HurricaneModel] = None


class OffShoreModel(BaseModel):
    wind: Optional[WindModel] = None
    rainfall: Optional[RainfallModel] = None
    tide: Optional[TideModel] = None
    hurricane: Optional[HurricaneModel] = None


class EventModel(BaseModel):
    """BaseModel describing all variables and data types of attributes common to all event types"""

    # Every event
    name: str
    mode: Mode  # single / risk
    time: TimeModel  # -> time.timing = [historical, idealized]

    # Optional parameters used by all Event child classes
    description: Optional[str] = None
    overland: Optional[OverlandModel] = None  # What to do with hurricane?
    offshore: Optional[OffShoreModel] = None  # What to do with hurricane?

    water_level_offset: Optional[UnitfulLength] = UnitfulLength(
        0, UnitTypesLength.meters
    )

    @model_validator(mode="after")
    def validate_eventModel(self):
        if self.mode == Mode.single_event:
            if self.time is None:
                raise ValueError("Time must be set when mode is single_event")
            elif self.water_level_offset is None:
                raise ValueError(
                    "Water level offset must be set when mode is single_event"
                )
        return self


# TODO investigate
class EventSetModel(BaseModel):
    """BaseModel describing the expected variables and data types of attributes common to a risk event that describes the probabilistic event set"""

    # add WindModel etc as this is shared among all? templates
    # TODO validate
    name: str
    mode: Mode
    description: Optional[str] = None
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


# #### SYNTHETIC ####
# class SyntheticEventModel(EventModel):
#     """BaseModel describing the expected variables and data types for parameters of Synthetic that extend the parent class Event"""

#     template: Template = Template.synthetic
#     timing: Timing = Timing.idealized

#     @model_validator(mode="after")
#     def validate_syntheticEventModel(self):
#         if self.template != Template.synthetic:
#             raise ValueError("Template for a Synthetic event must be synthetic")
#         elif self.timing != Timing.idealized:
#             raise ValueError("Timing for a Synthetic event must be idealized")
#         return self


# #### HISTORICAL #### should be read-only
# class HistoricalEventModel(EventModel):
#     """BaseModel describing the expected variables and data types for parameters of Historical that extend the parent class Event"""

#     template: Template = Template.historical
#     timing: Timing = Timing.historical

#     @model_validator(mode="after")
#     def validate_historicalEventModel(self):
#         if self.template != Template.historical:
#             raise ValueError("Template for a Historical event must be historical")
#         elif self.timing != Timing.historical:
#             raise ValueError("Historical events must have historical timing")
#         return self


# #### NEARSHORE ####
# class NearShoreEventModel(EventModel):
#     """BaseModel describing the expected variables and data types for parameters of Nearshore that extend the parent class Event"""

#     template: Template = Template.historical

#     @model_validator(mode="after")
#     def validate_nearshoreEventModel(self):
#         if self.template != Template.historical:
#             raise ValueError("Template for a Nearshore event must be historical")
#         return self


# #### OFFSHORE ####
# class OffShoreEventModel(EventModel):
#     """BaseModel describing the expected variables and data types for parameters of Offshore that extend the parent class Event"""

#     template: Template = Template.offshore

#     @model_validator(mode="after")
#     def validate_nearshoreEventModel(self):
#         if self.template != Template.offshore:
#             raise ValueError("Template for a Nearshore event must be offshore")
#         return self


# #### HURRICANE ####
# class HurricaneEventModel(EventModel):
#     """BaseModel describing the expected variables and data types for parameters of HistoricalHurricane that extend the parent class Event"""

#     template: Template = Template.hurricane
#     timing: Timing = Timing.historical
#     hurricane_translation: TranslationModel
#     track_name: str

#     @model_validator(mode="after")
#     def validate_hurricaneEventModel(self):
#         if self.template != Template.hurricane:
#             raise ValueError("Template for a Hurricane event must be hurricane")
#         elif self.timing != Timing.historical:
#             raise ValueError("Hurricane events must have historical timing")
#         return self
