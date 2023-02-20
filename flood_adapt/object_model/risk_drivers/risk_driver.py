from flood_adapt.object_model.io.config_io import read_config, write_config
from pathlib import Path
from typing import Union


class RiskDriver:
    def __init__(self, input_data: Union[str, Path, dict, None] = None) -> None:
        self.name = None
        self.config_file = None
        self.type = None
        self.input_data = input_data
    
    def read(self):
        if self.input_data:
            if isinstance(self.input_data, Path | str):
                self.config = read_config(self.input_data)
            elif isinstance(self.input_data, dict):
                self.config = self.input_data

    def write(out_path):
        write_config(out_path)

