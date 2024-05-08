from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDirection,
    UnitfulDischarge,
    UnitfulIntensity,
    UnitfulLength,
    UnitfulVelocity,
    UnitTypesLength,
)

from .objectModel import IDbsObject, DbsObjectModel


class Mode(str, Enum):
    """class describing the accepted input for the variable mode in Event"""

    single_event = "single_event"
    risk = "risk"


class Template(str, Enum):
    """class describing the accepted input for the variable template in Event"""

    Synthetic = "Synthetic"
    Hurricane = "Historical_hurricane"
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
    scs = "scs"


class WindModel(BaseModel):
    source: WindSource
    # constant
    constant_speed: Optional[UnitfulVelocity] = None
    constant_direction: Optional[UnitfulDirection] = None
    # timeseries
    timeseries_file: Optional[str] = None


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
    shape_duration: Optional[float] = None
    shape_peak_time: Optional[float] = None
    shape_start_time: Optional[float] = None
    shape_end_time: Optional[float] = None


class RiverModel(BaseModel):
    source: Optional[RiverSource] = None
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


class TimeModel(BaseModel):
    """BaseModel describing the expected variables and data types for time parameters of synthetic model"""

    duration_before_t0: Optional[float] = None
    duration_after_t0: Optional[float] = None
    start_time: Optional[str] = "20200101 000000"
    end_time: Optional[str] = "20200103 000000"


class TideSource(str, Enum):
    harmonic = "harmonic"
    timeseries = "timeseries"
    model = "model"


class TideModel(BaseModel):
    """BaseModel describing the expected variables and data types for harmonic tide parameters of synthetic model"""

    source: TideSource
    harmonic_amplitude: Optional[UnitfulLength] = None
    timeseries_file: Optional[str] = None


class SurgeSource(str, Enum):
    none = "none"
    shape = "shape"


class SurgeModel(BaseModel):
    """BaseModel describing the expected variables and data types for harmonic tide parameters of synthetic model"""

    source: SurgeSource
    shape_type: Optional[str] = "gaussian"
    shape_duration: Optional[float] = None
    shape_peak_time: Optional[float] = None
    shape_peak: Optional[UnitfulLength] = None


class TranslationModel(BaseModel):
    """BaseModel describing the expected variables and data types for translation parameters of hurricane model"""

    eastwest_translation: UnitfulLength = UnitfulLength(
        value=0.0, units=UnitTypesLength.meters
    )
    northsouth_translation: UnitfulLength = UnitfulLength(
        value=0.0, units=UnitTypesLength.meters
    )


class EventModel(
    DbsObjectModel
):  # add WindModel etc as this is shared among all? templates
    """BaseModel describing the expected variables and data types of attributes common to all event types"""

    mode: Mode
    template: Template
    timing: Timing
    water_level_offset: UnitfulLength
    wind: WindModel
    rainfall: RainfallModel
    river: list[RiverModel]
    time: TimeModel
    tide: TideModel
    surge: SurgeModel


class EventSetModel(
    BaseModel
):  # add WindModel etc as this is shared among all? templates
    """BaseModel describing the expected variables and data types of attributes common to a risk event that describes the probabilistic event set"""

    name: str = Field(..., min_length=1, pattern='^[^<>:"/\\\\|?* ]*$')
    description: Optional[str] = ""
    mode: Mode
    subevent_name: Optional[list[str]] = []
    frequency: Optional[list[float]] = []


class SyntheticModel(EventModel):  # add SurgeModel etc. that fit Synthetic event
    """BaseModel describing the expected variables and data types for parameters of Synthetic that extend the parent class Event"""


class HistoricalNearshoreModel(EventModel):
    """BaseModel describing the expected variables and data types for parameters of HistoricalNearshore that extend the parent class Event"""


class HistoricalOffshoreModel(EventModel):
    """BaseModel describing the expected variables and data types for parameters of HistoricalOffshore that extend the parent class Event"""


class HistoricalHurricaneModel(EventModel):
    """BaseModel describing the expected variables and data types for parameters of HistoricalHurricane that extend the parent class Event"""

    hurricane_translation: TranslationModel
    track_name: str


class IEvent(IDbsObject):
    attrs: EventModel


class ISynthetic(IEvent):
    attrs: SyntheticModel


class IHistoricalNearshore(IEvent):
    attrs: HistoricalNearshoreModel


class IHistoricalOffshore(IEvent):
    attrs: HistoricalOffshoreModel


class IHistoricalHurricane(IEvent):
    attrs: HistoricalHurricaneModel
