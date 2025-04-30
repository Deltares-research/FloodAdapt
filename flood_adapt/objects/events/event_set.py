import os
from pathlib import Path
from typing import List, Optional

import tomli
from pydantic import BaseModel

from flood_adapt.objects.events.events import Event, Mode
from flood_adapt.objects.object_model import Object


class SubEventModel(BaseModel):
    """The accepted input for a sub event in FloodAdapt.

    Attributes
    ----------
    name : str
        The name of the sub event.
    frequency : float
        The frequency of the sub event.
    """

    name: str
    frequency: float


class EventSet(Object):
    """BaseModel describing the expected variables and data types for parameters of EventSet.

    An EventSet is a collection of events that can be used to create a scenario and perform a probabilistoc risk assessment.

    Attributes
    ----------
    name : str
        The name of the event.
    description : str
        The description of the event. Defaults to "".
    mode : Mode
        The mode of the event. Defaults to Mode.risk.
    sub_events : List[SubEventModel]
        The sub events of the event set.
    """

    _events: Optional[List[Event]] = None

    mode: Mode = Mode.risk
    sub_events: List[SubEventModel]

    def load_sub_events(
        self,
        sub_events: Optional[List[Event]] = None,
        file_path: Optional[Path] = None,
    ) -> None:
        """Load sub events from a list or from a file path."""
        if sub_events is not None:
            self._events = sub_events
        elif file_path is not None:
            from flood_adapt.objects.events.event_factory import EventFactory

            sub_events = []
            for sub_event in self.sub_events:
                sub_toml = (
                    Path(file_path).parent / sub_event.name / f"{sub_event.name}.toml"
                )
                sub_events.append(EventFactory.load_file(sub_toml))

            self._events = sub_events
        else:
            raise ValueError("Either `sub_events` or `file_path` must be provided.")

    @classmethod
    def load_file(cls, file_path: Path | str | os.PathLike):
        """Load object from file."""
        with open(file_path, mode="rb") as fp:
            event_set = tomli.load(fp)
        event_set = EventSet(**event_set)
        event_set.load_sub_events(file_path=file_path)
        return event_set

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        for sub_event in self._events:
            sub_dir = Path(output_dir) / sub_event.name
            sub_dir.mkdir(parents=True, exist_ok=True)
            sub_event.save(sub_dir / f"{sub_event.name}.toml")
