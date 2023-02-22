from pathlib import Path

from flood_adapt.object_model.io.config_io import read_config, write_config
from flood_adapt.object_model.hazard.physical_projection.physical_projection import PhysicalProjection
from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.hazard.hazard_strategy.hazard_strategy import HazardStrategy
from flood_adapt.object_model.validate.config import validate_content_config_file, validate_existence_config_file

class Event:
    def __init__(self) -> None:
        self.set_default()

    def set_default(self):
        self.name = ""
        self.long_name = ""
        self.mode = ""
        self.event = [Event()]
        self.physical_projection = PhysicalProjection()
        # self.hazard_strategy = HazardStrategy()
        self.mandatory_keys = ["name", "long_name", "mode", "event", "physical_projection"]

    def set_name(self, value):
        self.name = value
    
    def set_long_name(self, value):
        self.long_name = value

    def set_physical_projection(self, value):
        self.physical_projection = PhysicalProjection.load("{}.toml".format(value))

    def set_event(self, value):
        self.event = Event.load("{}.toml".format(value))

    def set_hazard_strategy(self, value):
        self.hazard_strategy = HazardStrategy.load("{}.toml".format(value))
    
    def set_values(self, config_file: str = None):
        self.config_file = config_file
        if validate_existence_config_file(config_file):
            config = read_config(self.inputfile)

        if validate_content_config_file(config, config_file, self.mandatory_keys):
            self.set_name(config["name"])
            self.set_long_name(config["long_name"])
            self.set_physical_projection(config["projection"])
            self.set_event(config["event"])
            self.set_hazard_strategy(config["strategy"])
    
    # def write(self):
    #     write_config(self.config_file)