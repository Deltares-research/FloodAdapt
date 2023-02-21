
class PopulationGrowthExisting:
    def __init__(self) -> None:
        self.set_default()

    def set_default(self) -> None:
        self.value = 0
        self.type = "impact"
    
    def load(self, config: dict) -> None:
        self.value = config["population_growth_existing"]
