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
        obj.attrs = EventSetModel.model_validate(toml)
        return obj

    def __eq__(self, other):
        if not isinstance(other, EventSet):
            # don't attempt to compare against unrelated types
            return False

        # we're going to do some shenanigans so we can
        # test for equality without having to copy the very big objects
        # save attrs so we can erestore them later
        self_name = self.attrs.name
        other_name = other.attrs.name
        self_description = self.attrs.description
        other_description = other.attrs.description

        # set attrs to empty string so they don't invlucence result
        self.attrs.name = ""
        other.attrs.name = ""
        self.attrs.description = ""
        other.attrs.description = ""

        ans = self.attrs == other.attrs

        # restore
        self.attrs.name = self_name
        other.attrs.name = other_name
        self.attrs.description = self_description
        other.attrs.description = other_description

        return ans
