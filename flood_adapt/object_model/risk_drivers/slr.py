from flood_adapt.object_model.risk_drivers.risk_driver import RiskDriver

class SLR(RiskDriver):
    def __init__(self, config_path) -> None:
        super().__init__(config_path)
        