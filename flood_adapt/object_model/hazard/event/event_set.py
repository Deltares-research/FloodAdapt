import os
from pathlib import Path
from typing import Any, List

from pydantic import Field, model_validator
from typing_extensions import Annotated

from flood_adapt.object_model.hazard.event.template_event import (
    EventModel,
)
from flood_adapt.object_model.hazard.interface.events import IEvent, Mode
from flood_adapt.object_model.interface.database_user import DatabaseUser
from flood_adapt.object_model.interface.object_model import IObject, IObjectModel


class EventSetModel(IObjectModel):
    """BaseModel describing the expected variables and data types for parameters of Synthetic that extend the parent class Event."""

    mode: Mode = Mode.risk

    sub_events: List[EventModel]
    frequency: List[Annotated[float, Field(strict=True, ge=0, le=1)]]

    @model_validator(mode="before")
    def load_sub_events(self):
        """Load the sub events from the dictionary."""
        from flood_adapt.object_model.hazard.event.event_factory import EventFactory

        sub_events = [
            EventFactory.get_eventmodel_from_template(
                sub_event["template"]
            ).model_validate(sub_event)
            for sub_event in self["sub_events"]
        ]
        self["sub_events"] = sub_events
        return self

    def model_dump(self, **kwargs) -> dict[str, Any]:
        """Dump the model to a dictionary."""
        dump = super().model_dump(**kwargs)
        dump.update(forcings=[sub_event.model_dump() for sub_event in self.sub_events])
        return dump


class EventSet(IObject[EventSetModel], DatabaseUser):
    _attrs_type = EventSetModel

    events: List[IEvent]

    def __init__(self, data: dict[str, Any]) -> None:
        from flood_adapt.object_model.hazard.event.event_factory import EventFactory

        super().__init__(data)
        self.events = [
            EventFactory.load_dict(sub_event) for sub_event in self.attrs.sub_events
        ]

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
