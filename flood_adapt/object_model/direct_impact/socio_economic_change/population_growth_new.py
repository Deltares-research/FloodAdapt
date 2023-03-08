from typing import Union

from flood_adapt.object_model.validate.config import validate_content_config_file


class PopulationGrowthNew:
    def __init__(self) -> None:
        self.set_default()

    def set_default(self) -> None:
        self.population_growth_new = 0
        self.new_development_elevation = {
            "value": 0,
            "units": "m",
            "reference": "datum",
        }
        self.new_development_shapefile = ""

    def set_population_growth_new(self, value: Union[int, float]) -> None:
        self.population_growth_new = value

    def set_new_development_elevation(self, value: dict) -> None:
        self.new_development_elevation = value

    def set_new_development_shapefile(self, value: str) -> None:
        self.new_development_shapefile = value

    def load(self, config: dict, config_path: str) -> None:
        validate_content_config_file(
            config,
            config_path,
            [
                "population_growth_new",
                "new_development_elevation",
                "new_development_shapefile",
            ],
        )
        self.set_population_growth_new(config["population_growth_new"])
        self.set_new_development_elevation(config["new_development_elevation"])
        self.set_new_development_shapefile(config["new_development_shapefile"])

        return self
