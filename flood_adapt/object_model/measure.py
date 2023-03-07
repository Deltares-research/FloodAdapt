from abc import ABC
from flood_adapt.object_model.io.config_io import read_config
from flood_adapt.object_model.validate.config import (
    validate_existence_config_file,
    validate_content_config_file,
)

class Measure(ABC):
    """Measure parent class to create an ImpactMeasure or a HazardMeasure"""
    
    def set_default(self) -> None:
        """Sets the default values of the ImpactMeasure class attributes"""
        self.name = "Test2"  # Name of the measure
        self.long_name = ""  # Long name of the measure
        self.config_file = None  # path to the configuration file connected with the measure
        self.mandatory_keys = ["name", "long_name", "type"] # mandatory keys in the config file
    
    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    def long_name(self):
        return self._long_name
    
    @long_name.setter
    def long_name(self, value: str):
        self._long_name = value

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, value: str):
        self._type = value

    def load(self, config_file):
        """loads and updates the class attributes from a configuration file"""
        self.config_file = config_file
        # Validate the existence of the configuration file
        if validate_existence_config_file(self.config_file):
            self._config = read_config(self.config_file)

        # Validate that the mandatory keys are in the configuration file
        if validate_content_config_file(self._config, self.config_file, self.mandatory_keys):
            self.name = self._config["name"]
            self.long_name = self._config["long_name"]
            self.type = self._config["type"]