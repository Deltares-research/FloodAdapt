import os
from pathlib import Path
from typing import Any, List

import tomli
import tomli_w
from pydantic import BaseModel, Field
from typing_extensions import Annotated

from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.object_model.hazard.event.synthetic import SyntheticEventModel
from flood_adapt.object_model.hazard.interface.models import Mode
from flood_adapt.object_model.interface.database_user import DatabaseUser
from flood_adapt.object_model.interface.events import (
    IEvent,
    IEventModel,
)


class EventSetModel(BaseModel):
    """BaseModel describing the expected variables and data types for parameters of Synthetic that extend the parent class Event."""

    name: str
    description: str = ""
    mode: Mode = Mode.risk
    sub_events: List[IEventModel]
    frequency: List[Annotated[float, Field(strict=True, ge=0, le=1)]]

    @staticmethod
    def default() -> "EventSetModel":
        """Set default values for Synthetic event."""
        return EventSetModel(
            name="DefaultEventSet",
            sub_events=[SyntheticEventModel.default(), SyntheticEventModel.default()],
            frequency=[0.5, 0.5],
        )


class EventSet(DatabaseUser):
    logger = FloodAdaptLogging.getLogger(__name__)

    attrs: EventSetModel
    events: List[IEvent]

    @classmethod
    def load_dict(cls, attrs: dict[str, Any] | EventSetModel) -> "EventSet":
        from flood_adapt.object_model.hazard.event.event_factory import EventFactory

        obj = cls()
        obj.events = []
        sub_models = []
        if isinstance(attrs, EventSetModel):
            attrs = attrs.model_dump()

        for sub_event in attrs["sub_events"]:
            sub_event = EventFactory.load_dict(sub_event)
            if isinstance(sub_event, EventSet):
                raise ValueError("EventSet cannot contain other EventSets")
            obj.events.append(sub_event)
            sub_models.append(sub_event.attrs)

        attrs["sub_events"] = sub_models
        obj.attrs = EventSetModel.model_validate(attrs)
        return obj

    @classmethod
    def load_file(cls, path: Path) -> "EventSet":
        with open(path, "rb") as f:
            return cls.load_dict(tomli.load(f))

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            tomli_w.dump(self.attrs.model_dump(exclude_none=True), f)

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        for sub_event in self.events:
            sub_dir = Path(output_dir) / sub_event.attrs.name
            sub_dir.mkdir(parents=True, exist_ok=True)
            sub_event.save(sub_dir / f"{sub_event.attrs.name}.toml")

    def preprocess(self, output_dir: Path) -> None:
        """Prepare the forcings of the event set.

        Which is to say, prepare the forcings of the subevents of the event set.

        If the forcings require it, this function will:
        - download meteo data: download the meteo data from the meteo source and store it in the output directory.
        - preprocess and run offshore model: prepare and run the offshore model to obtain water levels for the boundary condition of the nearshore model.

        Then, it will call the process function of the subevents.

        """
        # @gundula, run offshore only once and then copy results?
        # Same for downloading meteo data
        # I dont think I've seen any code that changes the forcings of the subevents wrt eachother, is that correct?
        # So, just run the first subevent and then copy the results to the other subevents ?
        for sub_event in self.events:
            sub_event.preprocess(output_dir / sub_event.attrs.name)