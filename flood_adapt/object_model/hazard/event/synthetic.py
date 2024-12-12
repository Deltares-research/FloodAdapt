from pathlib import Path
from typing import ClassVar, List

from flood_adapt.object_model.hazard.event.template_event import Event, EventModel
from flood_adapt.object_model.hazard.interface.events import (
    ForcingSource,
    ForcingType,
    Template,
)
from flood_adapt.object_model.hazard.interface.models import TimeModel


class SyntheticEventModel(EventModel):
    """BaseModel describing the expected variables and data types for parameters of Synthetic that extend the parent class Event."""

    ALLOWED_FORCINGS: ClassVar[dict[ForcingType, List[ForcingSource]]] = {
        ForcingType.RAINFALL: [ForcingSource.CONSTANT, ForcingSource.SYNTHETIC],
        ForcingType.WIND: [ForcingSource.CONSTANT, ForcingSource.CSV],
        ForcingType.WATERLEVEL: [ForcingSource.SYNTHETIC, ForcingSource.CSV],
        ForcingType.DISCHARGE: [ForcingSource.CONSTANT, ForcingSource.SYNTHETIC],
    }
    template: Template = Template.Synthetic

    @classmethod
    def default(cls) -> "SyntheticEventModel":
        """Set default values for Synthetic event."""
        return cls(
            name="DefaultSyntheticEvent",
            time=TimeModel(),
        )


class SyntheticEvent(Event[SyntheticEventModel]):
    _attrs_type = SyntheticEventModel

    def preprocess(self, output_dir: Path):
        pass
