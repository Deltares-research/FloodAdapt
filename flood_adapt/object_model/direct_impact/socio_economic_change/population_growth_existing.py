from typing import Union

from flood_adapt.object_model.validate.config import validate_content_config_file


class PopulationGrowthExisting:
    def __init__(self) -> None:
        self.set_default()

    def set_default(self) -> None:
        self.population_growth_existing = 0

    def set_population_growth_existing(self, value: Union[int, float]) -> None:
        self.population_growth_existing = value

    def load(self, config: dict, config_path: str) -> None:
        validate_content_config_file(
            config, config_path, ["population_growth_existing"]
        )
        self.set_population_growth_existing(config["population_growth_existing"])

        return self
