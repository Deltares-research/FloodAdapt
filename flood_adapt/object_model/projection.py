from flood_adapt.object_model.io.config_io import read_config, write_config
from pathlib import Path
from typing import Union


class Projection:
    def __init__(self, inputfile: str) -> None:
        self.set_default()
        self.inputfile = inputfile

    def __init__(self):
        self.set_default()

    def set_default(self):
        self.name = ""
        self.config_file = None
        self.risk_drivers = []

    def set_name(self, value):
        self.name = value
    
    def set_risk_drivers(self):
        self.risk_drivers

    def load(self):
        if self.inputfile:
            if isinstance(self.inputfile, str):
                config = read_config(self.inputfile)

            self.set_name(config["name"])
            self.set_risk_drivers(config[""])
    
    # def write(self):
    #     write_config(self.config_file)
    

