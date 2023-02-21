
class EconomicGrowth:
    def __init__(self) -> None:
        self.set_default()

    def set_default(self) -> None:
        self.economic_growth = 0
        self.type = "impact"
    
    def load(self, config: dict) -> None:
        self.economic_growth = config["economic_growth"]
