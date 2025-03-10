import os
from pathlib import Path
from typing import Any, List, Optional

import tomli
from pydantic import BaseModel

from flood_adapt.object_model.hazard.interface.events import IEvent, Mode
from flood_adapt.object_model.interface.database_user import DatabaseUser
from flood_adapt.object_model.interface.object_model import IObject, IObjectModel


class SubEventModel(BaseModel):
    name: str
    frequency: float


class EventSetModel(IObjectModel):
    """BaseModel describing the expected variables and data types for parameters of Synthetic that extend the parent class Event."""

    mode: Mode = Mode.risk

    sub_events: List[SubEventModel]


class EventSet(IObject[EventSetModel], DatabaseUser):
    _attrs_type = EventSetModel

    events: List[IEvent]

    def __init__(
        self, data: dict[str, Any] | EventSetModel, sub_events: list[IEvent]
    ) -> None:
        super().__init__(data)
        self.events = sub_events

    def load_sub_events(
        self,
        sub_events: Optional[List[IEvent]] = None,
        file_path: Optional[Path] = None,
    ) -> None:
        """Load sub events from a list or from a file path."""
        if sub_events is not None:
            self.events = sub_events
        elif file_path is not None:
            from flood_adapt.object_model.hazard.event.event_factory import EventFactory

            sub_events = []
            for sub_event in self.attrs.sub_events:
                sub_event_toml = (
                    Path(file_path).parent / sub_event.name / f"{sub_event.name}.toml"
                )
                sub_events.append(EventFactory.load_file(sub_event_toml))

            self.events = sub_events
        else:
            raise ValueError("Either `sub_events` or `file_path` must be provided.")

    @classmethod
    def load_file(cls, file_path: Path | str | os.PathLike):
        """Load object from file."""
        from flood_adapt.object_model.hazard.event.event_factory import EventFactory

        with open(file_path, mode="rb") as fp:
            event_set = tomli.load(fp)

        sub_events = []
        for event_dict in event_set["sub_events"]:
            sub_toml = (
                Path(file_path).parent
                / event_dict["name"]
                / f"{event_dict['name']}.toml"
            )
            sub_events.append(EventFactory.load_file(sub_toml))

        return EventSet(event_set, sub_events)

    @classmethod
    def load_dict(cls, data: dict[str, Any] | EventSetModel, sub_events: list[IEvent]):
        """Load object from dictionary."""
        return EventSet(data, sub_events)

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        for sub_event in self.events:
            sub_dir = Path(output_dir) / sub_event.attrs.name
            sub_dir.mkdir(parents=True, exist_ok=True)
            sub_event.save(sub_dir / f"{sub_event.attrs.name}.toml")

    def preprocess(self, output_dir: Path) -> None:
        """Prepare the forcings of the event set.

        Which is to say, prepare the forcings of the subevents of the event set.

        If the forcings require it, this function will:
        - preprocess and run offshore model: prepare and run the offshore model to obtain water levels for the boundary condition of the nearshore model.

        Then, it will call the process function of the subevents.

        """
        for sub_event in self.events:
            sub_event.preprocess(output_dir / sub_event.attrs.name)
