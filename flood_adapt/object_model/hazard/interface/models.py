from datetime import datetime, timedelta
from enum import Enum
from typing import Union

from pydantic import BaseModel, field_serializer, field_validator

import flood_adapt.object_model.io.unitfulvalue as uv

### CONSTANTS ###
REFERENCE_TIME = datetime(year=2021, month=1, day=1, hour=0, minute=0, second=0)
TIDAL_PERIOD = uv.UnitfulTime(value=12.4, units=uv.UnitTypesTime.hours)
DEFAULT_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_TIMESTEP = uv.UnitfulTime(value=600, units=uv.UnitTypesTime.seconds)
TIMESERIES_VARIABLE = Union[
    uv.UnitfulIntensity,
    uv.UnitfulDischarge,
    uv.UnitfulVelocity,
    uv.UnitfulLength,
    uv.UnitfulHeight,
    uv.UnitfulArea,
    uv.UnitfulDirection,
]


### ENUMS ###
class ShapeType(str, Enum):
    gaussian = "gaussian"
    constant = "constant"
    triangle = "triangle"
    scs = "scs"


class Scstype(str, Enum):
    type1 = "type_1"
    type1a = "type_1a"
    type2 = "type_2"
    type3 = "type_3"


class Mode(str, Enum):
    """Class describing the accepted input for the variable mode in Event."""

    single_event = "single_event"
    risk = "risk"


class Template(str, Enum):
    """Class describing the accepted input for the variable template in Event."""

    Synthetic = "Synthetic"
    Hurricane = "Hurricane"
    Historical = "Historical"

    Historical_Hurricane = "Historical_hurricane"
    Historical_nearshore = "Historical_nearshore"
    Historical_offshore = "Historical_offshore"


class ForcingType(str, Enum):
    """Enum class for the different types of forcing parameters."""

    WIND = "WIND"
    RAINFALL = "RAINFALL"
    DISCHARGE = "DISCHARGE"
    WATERLEVEL = "WATERLEVEL"


class ForcingSource(str, Enum):
    """Enum class for the different sources of forcing parameters."""

    MODEL = "MODEL"  # 'our' hindcast/ sfincs offshore model
    TRACK = "TRACK"  # 'our' hindcast/ sfincs offshore model + (shifted) hurricane
    CSV = "CSV"  # user imported data

    SYNTHETIC = "SYNTHETIC"  # synthetic data
    CONSTANT = "CONSTANT"  # synthetic data

    GAUGED = "GAUGED"  # data downloaded from a gauge
    METEO = "METEO"  # external hindcast data


### MODELS ###
class TimeModel(BaseModel):
    start_time: datetime = REFERENCE_TIME
    end_time: datetime = REFERENCE_TIME + timedelta(days=1)
    time_step: timedelta = timedelta(minutes=10)

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def try_parse_datetime(cls, value: str | datetime) -> datetime:
        SUPPORTED_DATETIME_FORMATS = [
            "%Y%m%d %H%M%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S.%f%z",
        ]
        if not isinstance(value, datetime):
            for fmt in SUPPORTED_DATETIME_FORMATS:
                try:
                    value = datetime.strptime(value, fmt)
                    break
                except Exception:
                    pass

        if not isinstance(value, datetime):
            raise ValueError(
                f"Could not parse start time: {value}. Supported formats are {', '.join(SUPPORTED_DATETIME_FORMATS)}"
            )
        return value

    @field_serializer("time_step")
    @classmethod
    def serialize_time_step(cls, value: timedelta) -> float:
        return value.total_seconds()
