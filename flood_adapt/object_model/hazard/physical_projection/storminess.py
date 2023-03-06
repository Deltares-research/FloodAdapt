from flood_adapt.object_model.validate.config import validate_content_config_file
from typing import Union


class Storminess:
    def __init__(self) -> None:
        self.set_default()

    def set_default(self) -> None:
        self.storm_frequency_increase = 0

    def set_storm_frequency_increase(self, value: Union[float, int]):
        self.storm_frequency_increase = value

    def load(self, config: dict, config_path: str) -> None:
        validate_content_config_file(config, config_path, ["storm_frequency_increase"])
        self.storm_frequency_increase = config["storm_frequency_increase"]
        return self
