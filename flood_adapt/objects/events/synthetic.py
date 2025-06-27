from typing import ClassVar, List

from flood_adapt.objects.events.events import (
    Event,
    Template,
)
from flood_adapt.objects.forcing.forcing import (
    ForcingSource,
    ForcingType,
)


class SyntheticEvent(Event):
    """BaseModel describing the expected variables and data types for parameters of Synthetic that extend the parent class Event.

    Attributes
    ----------
    time : [TimeFrame](`flood_adapt.objects.forcing.time_frame.TimeFrame`)
        The time frame of the event.
    template : Template
        The template of the event. Defaults to Template.Synthetic.
    mode : Mode
        The mode of the event. Defaults to Mode.single_event.
    rainfall_multiplier : float
        The rainfall multiplier of the event. Defaults to 1.0.
    forcings : dict[ForcingType, list[IForcing]]
        The forcings of the event.
    """

    ALLOWED_FORCINGS: ClassVar[dict[ForcingType, List[ForcingSource]]] = {
        ForcingType.RAINFALL: [
            ForcingSource.CONSTANT,
            ForcingSource.SYNTHETIC,
        ],
        ForcingType.WIND: [
            ForcingSource.CONSTANT,
        ],
        ForcingType.WATERLEVEL: [
            ForcingSource.SYNTHETIC,
        ],
        ForcingType.DISCHARGE: [
            ForcingSource.SYNTHETIC,
            ForcingSource.CONSTANT,
        ],
    }
    template: Template = Template.Synthetic
