from flood_adapt.object_model.io.config_io import read_config


class RiskDriver:
    def __init__(self, config_path) -> None:
        self.config_path = config_path
        self.read()
    
    def read(self):
        self.config = read_config(self.config_path)
