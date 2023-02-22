from pathlib import Path

from flood_adapt.object_model.io.config_io import read_config, write_config
from flood_adapt.object_model.hazard.physical_projection.physical_projection import PhysicalProjection

class Event:
    def __init__(self) -> None:
        self.set_default()

    def set_default(self):
        self.name = ""
        self.long_name = ""
        self.mode = ""
        self.event = None
        self.ensemble = None
        self.physical_projection = PhysicalProjection()
        self.strategy = Strategy()
        self.mandatory_keys = ["name", "long_name", "template", "timing", "water_level_offset", "tide", "surge", "wind", "rainfall", "river"]

    def validate_existence_config_file(self):
        if self.config_file:
            if Path(self.config_file).is_file():
                return True
        
        raise FileNotFoundError("Cannot find event configuration file {}.".format(self.config_file))

    def validate_content_config_file(self, config):
        not_found_in_config = []
        for mandatory_key in self.mandatory_keys:
            if mandatory_key not in config.keys():
                not_found_in_config.append(mandatory_key)
        
        if not_found_in_config:
            raise ValueError("Cannot find mandatory key(s) '{}' in configuration file {}.".format(', '.join(not_found_in_config), self.config_file))
        else:
            return True

    def set_name(self, value):
        self.name = value
    
    def set_long_name(self, value):
        self.long_name = value
    
    def load(self):
        if self.validate_existence_config_file():
            config = read_config(self.inputfile)

        if self.validate_content_config_file(config):
            self.set_name(config["name"])
            self.set_long_name(config["long_name"])
    
    # def write(self):
    #     write_config(self.config_file)