from pathlib import Path
from typing import Any, ClassVar, List

from flood_adapt.object_model.hazard.event.forcing.forcing_factory import ForcingFactory
from flood_adapt.object_model.hazard.event.template_event import Event
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    ForcingType,
)
from flood_adapt.object_model.hazard.interface.models import Template, TimeModel
from flood_adapt.object_model.interface.events import (
    IEventModel,
    Mode,
)
from flood_adapt.object_model.interface.path_builder import (
    TopLevelDir,
    db_path,
)
from flood_adapt.object_model.interface.site import Site


class HistoricalEventModel(IEventModel):
    """BaseModel describing the expected variables and data types for parameters of HistoricalNearshore that extend the parent class Event."""

    ALLOWED_FORCINGS: ClassVar[dict[ForcingType, List[ForcingSource]]] = {
        ForcingType.RAINFALL: [
            ForcingSource.CONSTANT,
            ForcingSource.CSV,
            ForcingSource.METEO,
        ],
        ForcingType.WIND: [
            ForcingSource.CONSTANT,
            ForcingSource.CSV,
            ForcingSource.METEO,
        ],
        ForcingType.WATERLEVEL: [
            ForcingSource.CSV,
            ForcingSource.MODEL,
            ForcingSource.GAUGED,
        ],
        ForcingType.DISCHARGE: [ForcingSource.CONSTANT, ForcingSource.CSV],
    }

    @classmethod
    def default(cls) -> "HistoricalEventModel":
        """Set default values for Synthetic event."""
        return cls(
            name="DefaultHistoricalEvent",
            time=TimeModel(),
            template=Template.Historical,
            mode=Mode.single_event,
            forcings={
                ForcingType.RAINFALL: ForcingFactory.get_default_forcing(
                    ForcingType.RAINFALL, ForcingSource.METEO
                ),
                ForcingType.WIND: ForcingFactory.get_default_forcing(
                    ForcingType.WIND, ForcingSource.METEO
                ),
                ForcingType.WATERLEVEL: ForcingFactory.get_default_forcing(
                    ForcingType.WATERLEVEL, ForcingSource.MODEL
                ),
                ForcingType.DISCHARGE: ForcingFactory.get_default_forcing(
                    ForcingType.DISCHARGE, ForcingSource.CONSTANT
                ),
            },
        )


class HistoricalEvent(Event):
    MODEL_TYPE = HistoricalEventModel
    attrs: HistoricalEventModel

    def __init__(self, data: dict[str, Any]) -> None:
        if isinstance(data, HistoricalEventModel):
            self.attrs = data
        else:
            self.attrs = HistoricalEventModel.model_validate(data)
        self.site = Site.load_file(db_path(TopLevelDir.static) / "site" / "site.toml")

    def preprocess(self, output_dir: Path):
        pass