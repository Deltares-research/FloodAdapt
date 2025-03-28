from typing import ClassVar, List

from flood_adapt.object_model.hazard.event.template_event import Event, EventModel
from flood_adapt.object_model.hazard.interface.events import Template
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    ForcingType,
)


class HistoricalEventModel(EventModel):
    """BaseModel describing the expected variables and data types for parameters of HistoricalNearshore that extend the parent class Event."""

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


class HistoricalEvent(Event[HistoricalEventModel]):
    _attrs_type = HistoricalEventModel
