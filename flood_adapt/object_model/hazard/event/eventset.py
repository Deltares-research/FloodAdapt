from pathlib import Path
from typing import Any

from flood_adapt.object_model.interface.events import EventSetModel
from flood_adapt.object_model.interface.object_model import IObject
from flood_adapt.object_model.interface.path_builder import (
    ObjectDir,
)


class EventSet(IObject[EventSetModel]):
    """class for all event sets."""

    attrs: EventSetModel
    dir_name = ObjectDir.event
    event_paths: list[Path]

    def __init__(self, data: dict[str, Any]) -> None:
        if isinstance(data, EventSetModel):
            self.attrs = data
        else:
            self.attrs = EventSetModel.model_validate(data)
