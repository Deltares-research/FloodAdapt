from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, validator

from flood_adapt.object_model.hazard.event.forcing.discharge import (
    DischargeConstant,
    DischargeSynthetic,
    IDischarge,  # noqa
)
from flood_adapt.object_model.hazard.event.forcing.forcing import IForcing
from flood_adapt.object_model.hazard.event.forcing.rainfall import (
    IRainfall,
    RainfallConstant,
    RainfallFromModel,
    RainfallFromTrack,
    RainfallSynthetic,
)
from flood_adapt.object_model.hazard.event.forcing.waterlevels import (
    IWaterlevel,
    WaterlevelFromFile,
    WaterlevelFromModel,
    WaterlevelSynthetic,
)
from flood_adapt.object_model.hazard.event.forcing.wind import (
    IWind,
    WindConstant,
    WindFromModel,
    WindFromTrack,
    WindTimeSeries,
)
from flood_adapt.object_model.io.unitfulvalue import UnitfulLength, UnitTypesLength


class Mode(str, Enum):
    """Class describing the accepted input for the variable mode in Event."""

    single_event = "single_event"
    risk = "risk"


class Template(str, Enum):
    """Class describing the accepted input for the variable template in Event."""

    Synthetic = "Synthetic"
    Hurricane = "Historical_hurricane"
    Historical_nearshore = "Historical_nearshore"
    Historical_offshore = "Historical_offshore"


DEFAULT_START_TIME = datetime(year=2020, month=1, day=1, hour=0)
DEFAULT_END_TIME = datetime(year=2020, month=1, day=1, hour=3)


class TimeModel(BaseModel):
    start_time: datetime = DEFAULT_START_TIME
    end_time: datetime = DEFAULT_END_TIME
    time_step: timedelta = timedelta(minutes=10)


class TranslationModel(BaseModel):
    """BaseModel describing the expected variables and data types for translation parameters of hurricane model."""

    eastwest_translation: UnitfulLength = UnitfulLength(
        value=0.0, units=UnitTypesLength.meters
    )
    northsouth_translation: UnitfulLength = UnitfulLength(
        value=0.0, units=UnitTypesLength.meters
    )


class IEventModel(BaseModel):
    _ALLOWED_FORCINGS: List[IForcing] = []

    name: str
    description: Optional[str] = None
    time: TimeModel
    template: Template
    mode: Mode

    forcings: List[IForcing]

    @validator("forcings", each_item=True)
    def check_allowed_forcings(cls, v):
        if type(v) not in cls._ALLOWED_FORCINGS:
            raise ValueError(
                f"Forcing {v} not in allowed forcings {cls._ALLOWED_FORCINGS}"
            )
        return v

    @validator("forcings")
    def check_single_wind(cls, v):
        wind_count = sum(issubclass(forcing, IWind) for forcing in v)
        if wind_count > 1:
            raise ValueError("There can be only one Wind forcing")
        return v

    @validator("forcings")
    def check_single_rainfall(cls, v):
        rainfall_count = sum(issubclass(forcing, IRainfall) for forcing in v)
        if rainfall_count > 1:
            raise ValueError("There can be only one Rainfall forcing")
        return v

    @validator("forcings")
    def check_single_waterlevel(cls, v):
        waterlevel_count = sum(issubclass(forcing, IWaterlevel) for forcing in v)
        if waterlevel_count > 1:
            raise ValueError("There can be only one Waterlevel forcing")
        return v


class SyntheticEventModel(IEventModel):  # add SurgeModel etc. that fit Synthetic event
    """BaseModel describing the expected variables and data types for parameters of Synthetic that extend the parent class Event."""

    _ALLOWED_FORCINGS = [
        RainfallConstant,
        RainfallSynthetic,
        WindConstant,
        WindTimeSeries,
        WaterlevelSynthetic,
        WaterlevelFromFile,
        DischargeConstant,
        DischargeSynthetic,
    ]


class HistoricalEventModel(IEventModel):
    """BaseModel describing the expected variables and data types for parameters of HistoricalNearshore that extend the parent class Event."""

    _ALLOWED_FORCINGS = [
        RainfallConstant,
        # RainfallSynthetic,
        RainfallFromModel,
        WindConstant,
        # WindTimeSeries,
        WindFromModel,
        # WaterlevelSynthetic,
        WaterlevelFromFile,
        WaterlevelFromModel,
        DischargeConstant,
        # DischargeSynthetic,
    ]


class HurricaneEventModel(IEventModel):
    """BaseModel describing the expected variables and data types for parameters of HistoricalHurricane that extend the parent class Event."""

    _ALLOWED_FORCINGS = [
        RainfallConstant,
        # RainfallSynthetic,
        RainfallFromModel,
        RainfallFromTrack,
        # WindConstant,
        # WindTimeSeries,
        WindFromTrack,
        # WaterlevelSynthetic,
        # WaterlevelFromFile,
        WaterlevelFromModel,
        DischargeConstant,
        DischargeSynthetic,
    ]

    hurricane_translation: TranslationModel
    track_name: str


class EventSetModel(IEventModel):
    """BaseModel describing the expected variables and data types for parameters of Synthetic that extend the parent class Event."""

    _ALLOWED_FORCINGS = [
        RainfallConstant,
        RainfallSynthetic,
        WindConstant,
        WindTimeSeries,
        WaterlevelSynthetic,
        WaterlevelFromFile,
        DischargeConstant,
        DischargeSynthetic,
    ]
