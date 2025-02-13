from pathlib import Path
from typing import ClassVar, List

from flood_adapt.object_model.hazard.event.template_event import Event, EventModel
from flood_adapt.object_model.hazard.interface.events import (
    ForcingSource,
    ForcingType,
    Template,
)


class SyntheticEventModel(EventModel):
    """BaseModel describing the expected variables and data types for parameters of Synthetic that extend the parent class Event."""

    ALLOWED_FORCINGS: ClassVar[dict[ForcingType, List[ForcingSource]]] = {
        ForcingType.RAINFALL: [
            ForcingSource.CONSTANT,
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


class SyntheticEvent(Event[SyntheticEventModel]):
    _attrs_type = SyntheticEventModel

    def preprocess(self, output_dir: Path):
        pass
