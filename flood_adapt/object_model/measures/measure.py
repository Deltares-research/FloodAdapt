from flood_adapt.object_model.io.config_io import read_config

class Measure:
    def __init__(self, config_file: str = None):
        self.set_default()
        if config_file:
            self.config_file = config_file

    def set_default(self):
        self.name = ""
        self.long_name = ""
        self.config_file = None
        self.type = ""

    def set_name(self, name: str):
        self.name = name
    
    def set_long_name(self, long_name: str):
        self.long_name = long_name
    
    def set_type(self, type: str):
        self.type = type

    def load(self):
        if self.config_file:
            if isinstance(self.config_file, str):
                config = read_config(self.config_file)

            self.set_name(config["name"])
            self.set_long_name(config["long_name"])
            self.set_type(config["type"])
