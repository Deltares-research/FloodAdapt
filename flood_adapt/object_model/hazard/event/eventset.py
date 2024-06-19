from pathlib import Path
from typing import Union

import tomli

from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.hazard.event.event_factory import EventFactory
from flood_adapt.object_model.interface.events import EventSetModel


class EventSet:
    """class for all event sets."""

    attrs: EventSetModel
    event_paths: list[Path]

    @staticmethod
    def load_file(filepath: Union[str, Path]):
        """Create risk event from toml file."""
        obj = EventSet()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = EventSetModel.model_validate(toml)
        return obj

    def get_subevents(self) -> list[Event]:
        # parse event config file to get event template
        event_list = []
        for event_path in self.event_paths:
            template = Event.get_template(event_path)
            # use event template to get the associated event child class
            event_list.append(EventFactory.get_event(template).load_file(event_path))
        return event_list

    def __eq__(self, other):
        if not isinstance(other, EventSet):
            # don't attempt to compare against unrelated types
            return NotImplemented
        attrs_1, attrs_2 = self.attrs.copy(), other.attrs.copy()
        attrs_1.__delattr__("name"), attrs_2.__delattr__("name")
        attrs_1.__delattr__("description"), attrs_2.__delattr__("description")
        return attrs_1 == attrs_2
