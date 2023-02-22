from flood_adapt.object_model.validate.config import validate_content_config_file
from typing import Union


class PrecipitationIntensity:
    def __init__(self) -> None:
        self.set_default()

    def set_default(self) -> None:
        self.effect_on = "hazard"
        self.rainfall_increase = 0
    
    def set_rainfall_increase(self, value: Union[int, float]) -> None:
        self.rainfall_increase = value

    def load(self, config: dict, config_path: str) -> None:
        validate_content_config_file(config, config_path, ["rainfall_increase"])
        self.set_rainfall_increase(config["rainfall_increase"])
