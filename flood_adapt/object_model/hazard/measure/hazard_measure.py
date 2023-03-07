from flood_adapt.object_model.io.config_io import read_config
from flood_adapt.object_model.validate.config import (
    validate_content_config_file,
    validate_existence_config_file,
)


class HazardMeasure:
    """Measure class that holds all the information for a specific measure type"""

    def __init__(self) -> None:
        self.set_default()

    def set_default(self):
        """Sets the default values of the Measure class attributes"""
        self.name = ""  # Name of the measure
        self.long_name = ""  # Long name of the measure
        self.config_file = (
            None  # path to the configuration file connected with the measure
        )
        self.type = ""  # type of the measure
        self.mandatory_keys = ["name", "long_name"]  # mandatory keys in the config file

    def set_name(self, name: str):
        self.name = name

    def set_long_name(self, long_name: str):
        self.long_name = long_name

    def load(self, config_file: str = None):
        """loads and updates the class attributes from a configuration file"""
        # Validate the existence of the configuration file
        if validate_existence_config_file(config_file):
            config = read_config(config_file)

            self.config_file = config_file

            # Validate that the mandatory keys are in the configuration file
            if validate_content_config_file(
                config, self.config_file, self.mandatory_keys
            ):
                self.set_name(config["name"])
                self.set_long_name(config["long_name"])
