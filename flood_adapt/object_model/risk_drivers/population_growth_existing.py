
class PopulationGrowthExisting:
    def __init__(self) -> None:
        self.set_default()

    def set_default(self) -> None:
        self.population_growth_existing = 0
        self.type = "impact"
    
    def load(self, config: dict) -> None:
        self.population_growth_existing = config["population_growth_existing"]
