from flood_adapt.object_model.io.config_io import read_config, write_config
from pathlib import Path


class RiskDriver:
    def __init__(self, config: dict) -> None:
        self.name = None
        self.config = None
        self.type = None
    
    def set_default(self):
        

    def set_drivers(self):
        

    def read(self):
        if self.input_data:
            if isinstance(self.input_data, Path | str):
                self.config = read_config(self.input_data)
            elif isinstance(self.input_data, dict):
                self.config = self.input_data

    def write(out_path):
        write_config(out_path)

