from pathlib import Path
from typing import Any, ClassVar, List

from flood_adapt.object_model.hazard.event.template_event import Event, EventModel
from flood_adapt.object_model.hazard.interface.events import Template
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    ForcingType,
)
from flood_adapt.object_model.hazard.interface.models import TimeModel
from flood_adapt.object_model.interface.path_builder import (
    TopLevelDir,
    db_path,
)
from flood_adapt.object_model.interface.site import Site


class HistoricalEventModel(EventModel):
    """BaseModel describing the expected variables and data types for parameters of HistoricalNearshore that extend the parent class Event."""

    ALLOWED_FORCINGS: ClassVar[dict[ForcingType, List[ForcingSource]]] = {
        ForcingType.RAINFALL: [
            ForcingSource.CONSTANT,
            ForcingSource.CSV,
            ForcingSource.METEO,
            ForcingSource.SYNTHETIC,
        ],
        ForcingType.WIND: [
            ForcingSource.CONSTANT,
            ForcingSource.CSV,
            ForcingSource.METEO,
            ForcingSource.SYNTHETIC,
        ],
        ForcingType.WATERLEVEL: [
            ForcingSource.CSV,
            ForcingSource.MODEL,
            ForcingSource.GAUGED,
            ForcingSource.SYNTHETIC,
        ],
        ForcingType.DISCHARGE: [
            ForcingSource.CONSTANT,
            ForcingSource.CSV,
            ForcingSource.SYNTHETIC,
        ],
    }
    template: Template = Template.Historical

    @classmethod
    def default(cls) -> "HistoricalEventModel":
        """Set default values for Synthetic event."""
        return HistoricalEventModel(
            name="DefaultHistoricalEvent",
            time=TimeModel(),
        )


class HistoricalEvent(Event[HistoricalEventModel]):
    _attrs_type = HistoricalEventModel

    def __init__(self, data: dict[str, Any]) -> None:
        super().__init__(data)
        self.site = Site.load_file(db_path(TopLevelDir.static) / "site" / "site.toml")

    def preprocess(self, output_dir: Path):
        pass
