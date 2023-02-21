from flood_adapt.object_model.validate.config import validate_content_config_file


class PopulationGrowthNew:
    def __init__(self) -> None:
        self.set_default()

    def set_default(self) -> None:
        self.effect_on = "impact"
        self.value = 0
        self.new_development_elevation = {"value": 0, "units": "m", "reference": "Datum"}  ## What was the other option again besides "floodmap"?
        self.new_development_shapefile = ""
    
    def load(self, config: dict, config_path: str) -> None:
        validate_content_config_file(config, config_path, ["population_growth_new", "new_development_elevation", "new_development_shapefile"])
        self.value = config["population_growth_new"]
        self.new_development_elevation = config["new_development_elevation"]
        self.new_development_shapefile = config["new_development_shapefile"]
