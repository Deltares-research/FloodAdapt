
class Storminess:
    def __init__(self) -> None:
        self.set_default()

    def set_default(self) -> None:
        self.storm_frequency_increase = 0
        self.type = "hazard"
    
    def load(self, config: dict) -> None:
        self.storm_frequency_increase = config["storm_frequency_increase"]
