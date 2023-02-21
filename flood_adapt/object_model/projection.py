from flood_adapt.object_model.io.config_io import read_config, write_config
from flood_adapt.object_model.risk_drivers.risk_driver import RiskDriver
from pathlib import Path


class Projection:
    def __init__(self, config_file: str = None) -> None:
        self.set_default()
        if config_file:
            self.config_file = config_file

    def set_default(self):
        self.name = ""
        self.config_file = None
        self.risk_drivers = []
        self.mandatory_keys = ["name", "long_name"]

    def validate_existence_config_file(self):
        if self.config_file:
            if Path(self.config_file).is_file():
                return True
        
        raise FileNotFoundError("Cannot find projection configuration file {}.".format(self.config_file))

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
    
    def set_risk_drivers(self, config):
        self.risk_drivers = RiskDriver()
    
    def load(self):
        if self.validate_existence_config_file():
            config = read_config(self.inputfile)

        if self.validate_content_config_file(config):
            self.set_name(config["name"])
            self.set_name(config["long_name"])
            self.set_risk_drivers(config)
    
    # def write(self):
    #     write_config(self.config_file)
    

