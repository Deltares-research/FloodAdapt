from flood_adapt.object_model.risk_drivers.risk_driver import RiskDriver


class SLR(RiskDriver):
    def __init__(self) -> None:
        super().__init__()

        self.value = 0
        self.type = "hazard"
    
    def read(self, config_path):
        if config_path.exists():
            read_config(self.config_path)
        self.value = self.config["value"]
        