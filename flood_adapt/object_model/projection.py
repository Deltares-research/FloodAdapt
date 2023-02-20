from flood_adapt.object_model.io.config_io import read_config, write_config
from pathlib import Path
from typing import Union


class Projection:
    def __init__(self, input_data: Union[str, Path, dict, None] = None) -> None:
        self.name = ""
        self.toml_file = None
        self.risk_drivers = []
        self.input_data = input_data

    def read(self):
        if self.input_data:
            if isinstance(self.input_data, Path | str):
                self.config = read_config(self.input_data)
            elif isinstance(self.input_data, dict):
                self.config = self.input_data
    
    def write(self):
        write_config(self.toml_file)
