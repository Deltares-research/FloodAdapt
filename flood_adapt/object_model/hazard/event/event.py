from flood_adapt.object_model.io.config_io import read_config
from flood_adapt.object_model.validate.config import (
    validate_content_config_file,
    validate_existence_config_file,
)


class Event:
    def __init__(self) -> None:
        self.set_default()

    def set_default(self):
        self.name = ""
        self.long_name = ""
        self.template = ""
        self.timing = ""
        self.water_level_offset = {}
        self.tide = {}
        self.surge = {}
        self.wind = {}
        self.rainfall = {}
        self.river = {}
        self.config_file = None
        self.mandatory_keys = [
            "name",
            "long_name",
            "template",
            "timing",
            "water_level_offset",
            "tide",
            "surge",
            "wind",
            "rainfall",
            "river",
        ]

    def set_name(self, value):
        self.name = value

    def set_long_name(self, value):
        self.long_name = value

    def set_template(self, value: str) -> None:
        self.template = value

    def set_timing(self, value: str) -> None:
        self.timing = value

    def load(self, config_file: str = None):
        self.config_file = config_file
        if validate_existence_config_file(config_file):
            config = read_config(self.config_file)

            if validate_content_config_file(config, config_file, self.mandatory_keys):
                self.set_name(config["name"])
                self.set_long_name(config["long_name"])
                self.set_template(config["template"])
                self.set_timing(config["timing"])
        return self

    # def write(self):
    #     write_config(self.config_file)
