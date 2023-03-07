from typing import Union

from flood_adapt.object_model.validate.config import validate_content_config_file


class SLR:
    def __init__(self) -> None:
        self.set_default()

    def set_default(self) -> None:
        self.slr = {"value": 0, "units": "m"}
        self.subsidence = {"value": 0, "units": "m"}

    def set_slr(self, value: Union[int, float]) -> None:
        self.slr = value

    def set_subsidence(self, value: Union[int, float]) -> None:
        self.subsidence = value

    def load(self, config: dict, config_path: str) -> None:
        validate_content_config_file(
            config, config_path, ["sea_level_rise", "subsidence"]
        )
        self.set_slr(config["sea_level_rise"])
        self.set_subsidence(config["subsidence"])
        return self
