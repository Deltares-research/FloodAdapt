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


# Enums
class Mode(str, Enum):
    """class describing the accepted input for the variable mode in Event"""

    single_event = "single_event"
    risk = "risk"


class ShapeType(str, Enum):
    gaussian = "gaussian"
    constant = "constant"
    triangle = "triangle"
    csv_file = "csv_file"
    harmonic = "harmonic"
    scs = "scs"


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
    multiplier: float = 1.0
    timeseries: Optional[TimeseriesModel] = None

    @field_validator("multiplier")
    @classmethod
    def validate_multiplier(cls, value):
        if value < 0:
            raise ValueError("Multiplier must be positive")
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

    @model_validator(mode="after")
    def validate_riverDischargeModel(self):
        if not isinstance(self.timeseries.peak_intensity, UnitfulDischarge):
            raise ValueError(
                "Peak intensity must be a UnitfulDischarge when describing a river discharge"
            )
        return self


class Timing(str, Enum):
    """class describing the accepted input for the variable timng in Event"""

    historical = "historical"
    idealized = "idealized"


DEFAULT_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_TIMESTEP = UnitfulTime(600, UnitTypesTime.seconds)
DEFAULT_START_TIME = "2020-01-01 00:00:00"
DEFAULT_END_TIME = "2020-01-03 00:00:00"


class TimeModel(BaseModel):
    """
    BaseModel describing the start and end times of an event model.
    Used by all event types.
    In the format of a string that is parsed as a datetime object, e.g. "2020-01-01 00:00:00" (YYYY-MM-DD HH:MM:SS)
    """

    start_time: str = DEFAULT_START_TIME
    end_time: str = DEFAULT_END_TIME

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time_format(cls, value):
        try:
            datetime.strptime(value, DEFAULT_DATETIME_FORMAT)
        except ValueError:
            raise ValueError(
                f"Time must be in format {DEFAULT_DATETIME_FORMAT}. Got {value}"
            )
        return value

    @model_validator(mode="after")
    def validate_timeModel(self):
        if datetime.strptime(
            self.start_time, DEFAULT_DATETIME_FORMAT
        ) > datetime.strptime(self.end_time, DEFAULT_DATETIME_FORMAT):
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
    gauged: bool = False


class OffShoreModel(BaseModel):
    wind: Optional[WindModel] = None
    rainfall: Optional[RainfallModel] = None
    tide: Optional[TideModel] = None

    hurricane: Optional[HurricaneModel] = None
    water_level_offset: Optional[UnitfulLength] = None

    @field_validator("water_level_offset")
    @classmethod
    def validate_water_level_offset(cls, value):
        if value is None:
            raise ValueError(
                "Water level offset must be set when running an offshore event"
            )
        return value


class EventModel(BaseModel):
    """BaseModel describing all variables and data types of attributes common to all event types"""

    # Required attrs & models
    name: str  # -> name of the event
    mode: Mode  # -> single / risk
    time: TimeModel  # -> start_time, end_time as datetime objects

    # Optional attrs & models
    description: Optional[str] = None
    overland: Optional[OverlandModel] = None
    offshore: Optional[OffShoreModel] = None


# TODO investigate
class EventSetModel(BaseModel):
    """BaseModel describing the expected variables and data types of attributes common to a risk event that describes the probabilistic event set"""

    # add WindModel etc as this is shared among all? templates
    # TODO validate
    name: str
    mode: Mode
    description: Optional[str] = None
    subevent_name: Optional[list[str]] = None
    frequency: Optional[list[float]] = None


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
