from pathlib import Path
import tomli
from pydantic import BaseModel, ValidationError
from enum import Enum

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

class Timing(str, Enum):
    historical = "historical"
    idealized = "idealized"

class EventModel(BaseModel):
    name: str
    long_name : str
    mode : Mode
    template : Template
    timing : Timing
    water_level_offset : UnitfulValue

class Event:

    name: str
    long_name : str
    mode: str
    template : str
    timing : str
    water_level_offset : UnitfulValue
    filepath : str
    # tide : dict()
    # surge : dict()
    # wind : dict()
    # rainfall : dict()
    # river : dict()

    def __init__(self) -> None:
        self.set_default()

    def set_default(self):
        self.name = ""
        self.long_name = ""
        self.mode = ""
        self.template = ""
        self.timing = ""
        self.water_level_offset = UnitfulValue(value=0, units="m")
        self.filepath = None
        # self.tide = dict()
        # self.surge = dict()
        # self.wind = dict()
        # self.rainfall = dict()
        # self.river = dict()
        # self.mandatory_keys = [
        #     "name",
        #     "long_name",
        #     "template",
        #     "timing",
        #     "water_level_offset",
        #     "tide",
        #     "surge",
        #     "wind",
        #     "rainfall",
        #     "river",
        # ]

    def set_name(self, value) -> None:
        self.name = value

    def set_long_name(self, value) -> None:
        self.long_name = value

    def set_mode(self, value = Mode) -> None:
        self.long_name = value

    def set_template(self, value: Template) -> None:
        self.template = value

    def set_timing(self, value: Timing) -> None:
        self.timing = value

    def set_water_level_offset(self, water_level_offset: UnitfulValue) -> None:
        self.water_level_offset = water_level_offset

    def load(self, filepath: str):
        self.filepath = filepath
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        try:
            event = EventModel.parse_obj(toml)
        except ValidationError as e:
            print(e)

        # if validate_existence_config_file(config_file):
        #     config = read_config(self.config_file)

            # if validate_content_config_file(config, config_file, self.mandatory_keys):
        self.set_name(event.name)
        self.set_long_name(event.long_name)
        self.set_template(event.template)
        self.set_timing(event.timing)
        self.set_water_level_offset(event.water_level_offset)
        return self

    # def write(self):
    #     write_config(self.config_file)
