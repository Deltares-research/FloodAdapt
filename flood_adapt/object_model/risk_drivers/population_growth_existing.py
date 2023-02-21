from flood_adapt.object_model.validate.config import validate_content_config_file


class PopulationGrowthExisting:
    def __init__(self) -> None:
        self.set_default()

    def set_default(self) -> None:
        self.effect_on = "impact"
        self.value = 0
    
    def load(self, config: dict, config_path: str) -> None:
        validate_content_config_file(config, config_path, ["population_growth_existing"])
        self.value = config["population_growth_existing"]
