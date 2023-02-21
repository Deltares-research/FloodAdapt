
class PrecipitationIntensity:
    def __init__(self) -> None:
        self.set_default()

    def set_default(self) -> None:
        self.rainfall_increase = 0
        self.type = "hazard"
    
    def load(self, config: dict) -> None:
        self.rainfall_increase = config["rainfall_increase"]
