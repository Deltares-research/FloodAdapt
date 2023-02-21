
class PrecipitationIntensity:
    def __init__(self) -> None:
        self.set_default()

    def set_default(self) -> None:
        self.value = 0
        self.type = "hazard"
    
    def load(self, config: dict) -> None:
        self.value = config["rainfall_increase"]
