from flood_adapt.object_model.risk_drivers.risk_driver import RiskDriver


class SLR(RiskDriver):
    def __init__(self) -> None:
        super().__init__()
        self.set_default()
    
    def set_default(self) -> None:
        self.slr_value = 0
        self.slr_unit = "m"
        self.subsidence_value = 0
        self.subsidence_unit = "m"
        self.type = "hazard"
    
    def load(self, config: dict) -> None:
        self.slr_value = config["sea_level_rise"]
        self.slr_unit = config["sea_level_rise_vertical_units"]
        self.subsidence_value = config["subsidence"]
        self.subsidence_unit = config["subsidence_vertical_units"]
