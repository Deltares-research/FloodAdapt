from flood_adapt.object_model.io.config_io import read_config
from flood_adapt.object_model.validate.config import validate_existence_config_file, validate_content_config_file

from flood_adapt.object_model.risk_drivers.risk_driver_factory import RiskDriverFactory

from pathlib import Path


class Projection:
    def __init__(self, config_file: str = None) -> None:
        self.set_default()
        if config_file:
            self.config_file = config_file

    def set_default(self):
        self.name = ""
        self.config_file = None
        self.risk_driver = None
        self.mandatory_keys = ["name", "long_name"]

    def set_name(self, value):
        self.name = value
    
    def set_long_name(self, value):
        self.long_name = value
    
    def set_risk_drivers(self, config):
        # Load all risk drivers
        self.slr = SLR()
        self.slr.load(config)

        self.
        
    
    def load(self):
        # Validate the existence of the configuration file
        if validate_existence_config_file(self.config_file):
            config = read_config(self.config_file)

        # Validate that the mandatory keys are in the configuration file
        if validate_content_config_file(config, self.config_file, self.mandatory_keys):
            self.set_name(config["name"])
            self.set_name(config["long_name"])
            self.set_risk_drivers(config)
    
    # def write(self):
    #     write_config(self.config_file)
    

