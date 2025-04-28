from typing import ClassVar, List

from flood_adapt.objects.events.events import Event, Template
from flood_adapt.objects.forcing.forcing import (
    ForcingSource,
    ForcingType,
)
from flood_adapt.objects.forcing.time_frame import TimeFrame

__all__ = ["HistoricalEvent", "TimeFrame"]


class HistoricalEvent(Event):
    """BaseModel describing the expected variables and data types for parameters of HistoricalEvent that extend the parent class Event.

    Attributes
    ----------
    name : str
        The name of the event.
    description : str
        The description of the event. Defaults to "".
    time : TimeFrame
        The time frame of the event.
    template : Template
        The template of the event. Defaults to Template.Historical.
    mode : Mode
        The mode of the event. Defaults to Mode.single_event.
    rainfall_multiplier : float
        The rainfall multiplier of the event. Defaults to 1.0.
    forcings : dict[ForcingType, list[IForcing]]
        The forcings of the event.
    """

    ALLOWED_FORCINGS: ClassVar[dict[ForcingType, List[ForcingSource]]] = {
        ForcingType.RAINFALL: [
            ForcingSource.CSV,
            ForcingSource.METEO,
            ForcingSource.SYNTHETIC,
            ForcingSource.CONSTANT,
        ],
        ForcingType.WIND: [
            ForcingSource.CSV,
            ForcingSource.METEO,
            ForcingSource.CONSTANT,
        ],
        ForcingType.WATERLEVEL: [
            ForcingSource.MODEL,
            ForcingSource.CSV,
            ForcingSource.SYNTHETIC,
            ForcingSource.GAUGED,
        ],
        ForcingType.DISCHARGE: [
            ForcingSource.CSV,
            ForcingSource.SYNTHETIC,
            ForcingSource.CONSTANT,
        ],
    }
    template: Template = Template.Historical
