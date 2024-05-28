from pathlib import Path
from typing import Union

import tomli

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
        obj.attrs = EventSetModel.parse_obj(toml)
        return obj

    def __eq__(self, other):
        if not isinstance(other, EventSet):
            # don't attempt to compare against unrelated types
            return NotImplemented
        attrs_1, attrs_2 = self.attrs.copy(), other.attrs.copy()
        attrs_1.__delattr__("name"), attrs_2.__delattr__("name")
        attrs_1.__delattr__("description"), attrs_2.__delattr__("description")
        return attrs_1 == attrs_2
