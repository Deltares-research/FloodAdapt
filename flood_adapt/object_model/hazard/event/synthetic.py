from typing import ClassVar, List

from flood_adapt.object_model.hazard.event.template_event import Event
from flood_adapt.object_model.hazard.interface.events import (
    ForcingSource,
    ForcingType,
    Template,
)


class SyntheticEvent(Event):
    """BaseModel describing the expected variables and data types for parameters of Synthetic that extend the parent class Event."""

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
