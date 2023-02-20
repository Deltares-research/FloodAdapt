from flood_adapt.object_model.io.config_io import read_config, write_config
from pathlib import Path

class Measure:
    def __init__(self) -> None:
        self.name = None
        self.type = None

    def read(self, config_path):
        config = read_config(config_path)

    def write(self, config_path):
        self.config = write_config(config_path)
