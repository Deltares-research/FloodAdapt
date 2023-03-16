from pathlib import Path

import tomli

from flood_adapt.object_model.interface.events import EventModel


class Event:
    """abstract parent class for all event types"""

    attrs: EventModel

    @staticmethod
    def generate_timeseries():
        ...

    @staticmethod
    def get_template(filepath: Path):
        """create Synthetic from toml file"""

        obj = Event()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = EventModel.parse_obj(toml)
        return obj.attrs.template

    @staticmethod
    def get_mode(filepath: Path):
        """create Synthetic from toml file"""

        obj = Event()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = EventModel.parse_obj(toml)
        return obj.attrs.mode
