from abc import ABC
from enum import Enum

import tomli
from pydantic import BaseModel

# from flood_adapt.object_model.io.config_io import read_config, write_config
# from flood_adapt.object_model.validate.config import (
#     validate_content_config_file,
#     validate_existence_config_file,
# )
from flood_adapt.object_model.io.unitfulvalue import UnitfulValue


class Mode(str, Enum):
    single_scenario = "single_scenario"
    risk = "risk"


class Template(str, Enum):
    Synthetic = "Synthetic"
    Hurricane = "Hurricane"


class Timing(str, Enum):
    historical = "historical"
    idealized = "idealized"


class EventModel(BaseModel):  # add WindModel etc as this is shared among all? templates
    name: str
    long_name: str
    mode: Mode
    template: Template
    timing: Timing
    water_level_offset: UnitfulValue


class Event(ABC):
    event_generic: EventModel
    filepath: str
    # tide : dict() # Add to the child classes, started with tide in Synthetic
    # surge : dict()
    # wind : dict()
    # rainfall : dict()
    # river : dict()

    def set_default(self):
        self.event_generic = EventModel(
            name="",
            long_name="",
            mode="single_scenario",
            template="Synthetic",
            timing="idealized",
            water_level_offset=UnitfulValue(value=0, units="meters"),
        )
        self.filepath = None

    def load(self, filepath: str):
        self.filepath = filepath
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        self.event_generic = EventModel.parse_obj(toml)
