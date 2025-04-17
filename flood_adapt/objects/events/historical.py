from typing import ClassVar, List

from flood_adapt.objects.events.events import Event, Template
from flood_adapt.objects.forcing.forcing import (
    ForcingSource,
    ForcingType,
)


class HistoricalEvent(Event):
    """BaseModel describing the expected variables and data types for parameters of HistoricalEvent that extend the parent class Event.

    Attributes
    ----------
    name : str
        The name of the event.
    description : str, default=""
        The description of the event.
    time : TimeFrame
        The time frame of the event.
    template : Template, default=Template.Historical
        The template of the event.
    mode : Mode, default=Mode.single_event
        The mode of the event.
    rainfall_multiplier : float, default=1.0
        The rainfall multiplier of the event.
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
