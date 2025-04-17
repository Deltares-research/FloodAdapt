from typing import ClassVar, List

from flood_adapt.objects.events.events import (
    Event,
    ForcingSource,
    ForcingType,
    Template,
)


class SyntheticEvent(Event):
    """BaseModel describing the expected variables and data types for parameters of Synthetic that extend the parent class Event.

    Attributes
    ----------
    time : TimeFrame
        The time frame of the event.
    template : Template, default=Template.Synthetic
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
            ForcingSource.CONSTANT,
            ForcingSource.CSV,
            ForcingSource.SYNTHETIC,
        ],
        ForcingType.WIND: [
            ForcingSource.CSV,
            ForcingSource.CONSTANT,
        ],
        ForcingType.WATERLEVEL: [
            ForcingSource.CSV,
            ForcingSource.SYNTHETIC,
        ],
        ForcingType.DISCHARGE: [
            ForcingSource.CSV,
            ForcingSource.SYNTHETIC,
            ForcingSource.CONSTANT,
        ],
    }
    template: Template = Template.Synthetic
