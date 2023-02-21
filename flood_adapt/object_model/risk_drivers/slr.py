
class SLR:
    def __init__(self) -> None:
        self.set_default()
    
    def set_default(self) -> None:
        self.slr = {"value": 0, "units": "m"}
        self.subsidence =  {"value": 0, "units": "m"}
        self.type = "hazard"
    
    def load(self, config: dict) -> None:
        self.slr = config["sea_level_rise"]
        self.subsidence = config["subsidence"]
