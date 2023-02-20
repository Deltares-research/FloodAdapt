from flood_adapt.object_model.io.config_io import read_config, write_config
from pathlib import Path
from typing import Union


class Projection:
    def __init__(self, input_data: Union[str, Path, dict, None] = None) -> None:
        self.name = ""
        self.config_file = None
        self.risk_drivers = []
        self.input_data = input_data

    def set_name(self, value):
        self.name = value
    
    def set_risk_drivers(self):
        self.risk_drivers

    def read(self):
        if self.input_data:
            if isinstance(self.input_data, Path | str):
                config = read_config(self.input_data)
            elif isinstance(self.input_data, dict):
                config = self.input_data
            
            self.set_name(config["name"])
            self.set_risk_drivers(config[""])
    
    def write(self):
        write_config(self.config_file)
    

