from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from flood_adapt.object_model.hazard.new_events.forcing.discharge import (
    DischargeConstant,
    DischargeSynthetic,
    IDischarge,  # noqa
)
from flood_adapt.object_model.hazard.new_events.forcing.forcing import (
    ForcingType,
    IForcing,
)
from flood_adapt.object_model.hazard.new_events.forcing.rainfall import (
    IRainfall,  # noqa
    RainfallConstant,
    RainfallFromModel,
    RainfallFromTrack,
    RainfallSynthetic,
)
from flood_adapt.object_model.hazard.new_events.forcing.waterlevels import (
    IWaterlevel,  # noqa
    WaterlevelFromFile,
    WaterlevelFromModel,
    WaterlevelSynthetic,
)
from flood_adapt.object_model.hazard.new_events.forcing.wind import (
    IWind,  # noqa
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
    _ALLOWED_FORCINGS: dict[ForcingType, List[IForcing]] = Field(default_factory=dict)

    name: str
    description: Optional[str] = None
    time: TimeModel
    template: Template
    mode: Mode

    forcings: dict[ForcingType, IForcing] = Field(
        default_factory={
            ForcingType.WATERLEVEL: None,
            ForcingType.WIND: None,
            ForcingType.RAINFALL: None,
            ForcingType.DISCHARGE: None,
        }
    )

    @model_validator(mode="after")
    def validate_forcings(self):
        for forcing_category, concrete_forcing in self.forcings.items():
            if forcing_category not in type(self)._ALLOWED_FORCINGS:
                raise ValueError(
                    f"Forcing {forcing_category} not in allowed forcings {type(self)._ALLOWED_FORCINGS}"
                )
            if concrete_forcing not in type(self)._ALLOWED_FORCINGS[forcing_category]:
                raise ValueError(
                    f"Forcing {concrete_forcing} not allowed for forcing category {forcing_category}. Only {', '.join(type(self)._ALLOWED_FORCINGS[forcing_category].__name__)} are allowed"
                )
        return self


class SyntheticEventModel(IEventModel):  # add SurgeModel etc. that fit Synthetic event
    """BaseModel describing the expected variables and data types for parameters of Synthetic that extend the parent class Event."""

    _ALLOWED_FORCINGS = {
        ForcingType.RAINFALL: [RainfallConstant, RainfallSynthetic],
        ForcingType.WIND: [WindConstant, WindTimeSeries],
        ForcingType.WATERLEVEL: [WaterlevelSynthetic, WaterlevelFromFile],
        ForcingType.DISCHARGE: [DischargeConstant, DischargeSynthetic],
    }


class HistoricalEventModel(IEventModel):
    """BaseModel describing the expected variables and data types for parameters of HistoricalNearshore that extend the parent class Event."""

    _ALLOWED_FORCINGS = {
        ForcingType.RAINFALL: [RainfallConstant, RainfallFromModel],
        ForcingType.WIND: [WindConstant, WindFromModel],
        ForcingType.WATERLEVEL: [WaterlevelFromFile, WaterlevelFromModel],
        ForcingType.DISCHARGE: [DischargeConstant],
    }


class HurricaneEventModel(IEventModel):
    """BaseModel describing the expected variables and data types for parameters of HistoricalHurricane that extend the parent class Event."""

    _ALLOWED_FORCINGS = {
        ForcingType.RAINFALL: [RainfallConstant, RainfallFromModel, RainfallFromTrack],
        ForcingType.WIND: [WindFromTrack],
        ForcingType.WATERLEVEL: [WaterlevelFromModel],
        ForcingType.DISCHARGE: [DischargeConstant, DischargeSynthetic],
    }

    hurricane_translation: TranslationModel
    track_name: str


class EventSetModel(IEventModel):
    """BaseModel describing the expected variables and data types for parameters of Synthetic that extend the parent class Event."""

    _ALLOWED_FORCINGS = {
        ForcingType.RAINFALL: [RainfallConstant, RainfallFromModel, RainfallFromTrack],
        ForcingType.WIND: [WindFromTrack],
        ForcingType.WATERLEVEL: [WaterlevelFromModel],
        ForcingType.DISCHARGE: [DischargeConstant, DischargeSynthetic],
    }
