from flood_adapt.object_model.risk_drivers.slr import SLR
from flood_adapt.object_model.risk_drivers.population_growth_existing import PopulationGrowthExisting
from flood_adapt.object_model.risk_drivers.population_growth_new import PopulationGrowthNew


class RiskDriverFactory:
    @staticmethod
    def get_risk_drivers(risk_driver: str):
        if risk_driver == 'slr':
            return SLR()
        elif risk_driver == 'population_growth_existing':
            return PopulationGrowthExisting()
        elif risk_driver == 'population_growth_new':
            return PopulationGrowthNew()
