from flood_adapt.object_model.validate.config import validate_content_config_file


class SLR:
    def __init__(self) -> None:
        self.set_default()
    
    def set_default(self) -> None:
        self.effect_on = "hazard"
        self.slr = {"value": 0, "units": "m"}
        self.subsidence =  {"value": 0, "units": "m"}
    
    def load(self, config: dict, config_path: str) -> None:
        validate_content_config_file(config, config_path, ["sea_level_rise", "subsidence"])
        self.slr = config["sea_level_rise"]
        self.subsidence = config["subsidence"]
