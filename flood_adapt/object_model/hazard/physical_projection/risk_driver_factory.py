from flood_adapt.object_model.hazard.physical_projection.precipitation_intensity import (
    PrecipitationIntensity,
)
from flood_adapt.object_model.hazard.physical_projection.slr import SLR
from flood_adapt.object_model.hazard.physical_projection.storminess import Storminess


class RiskDriverFactory:
    @staticmethod
    def get_risk_drivers(risk_driver: str):
        if risk_driver == "slr":
            return SLR()
        elif risk_driver == "precipitation_intensity":
            return PrecipitationIntensity()
        elif risk_driver == "storminess":
            return Storminess()
