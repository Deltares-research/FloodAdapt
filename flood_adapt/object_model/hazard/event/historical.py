from pathlib import Path
from typing import Any, ClassVar, List

from flood_adapt.object_model.hazard.event.template_event import Event, EventModel
from flood_adapt.object_model.hazard.interface.events import Template
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    ForcingType,
)
from flood_adapt.object_model.interface.config.site import Site
from flood_adapt.object_model.interface.path_builder import (
    TopLevelDir,
    db_path,
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

    def __init__(self, data: dict[str, Any] | HistoricalEventModel) -> None:
        super().__init__(data)
        self.site = Site.load_file(db_path(TopLevelDir.static) / "config" / "site.toml")

    def preprocess(self, output_dir: Path):
        pass
