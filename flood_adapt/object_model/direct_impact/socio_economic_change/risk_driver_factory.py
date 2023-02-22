from flood_adapt.object_model.risk_drivers.slr import SLR
from flood_adapt.object_model.risk_drivers.population_growth_existing import PopulationGrowthExisting
from flood_adapt.object_model.risk_drivers.population_growth_new import PopulationGrowthNew
from flood_adapt.object_model.risk_drivers.economic_growth import EconomicGrowth
from flood_adapt.object_model.risk_drivers.precipitation_intensity import PrecipitationIntensity
from flood_adapt.object_model.risk_drivers.storminess import Storminess


class RiskDriverFactory:
    @staticmethod
    def get_risk_drivers(risk_driver: str):
        if risk_driver == 'slr':
            return SLR()
        elif risk_driver == 'population_growth_existing':
            return PopulationGrowthExisting()
        elif risk_driver == 'population_growth_new':
            return PopulationGrowthNew()
        elif risk_driver == 'economic_growth':
            return EconomicGrowth()
        elif risk_driver == 'precipitation_intensity':
            return PrecipitationIntensity()
        elif risk_driver == 'storminess':
            return Storminess()
