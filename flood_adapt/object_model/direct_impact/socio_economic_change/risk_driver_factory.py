from flood_adapt.object_model.direct_impact.socio_economic_change.economic_growth import (
    EconomicGrowth,
)
from flood_adapt.object_model.direct_impact.socio_economic_change.population_growth_existing import (
    PopulationGrowthExisting,
)
from flood_adapt.object_model.direct_impact.socio_economic_change.population_growth_new import (
    PopulationGrowthNew,
)


class RiskDriverFactory:
    @staticmethod
    def get_risk_drivers(risk_driver: str):
        if risk_driver == "economic_growth":
            return EconomicGrowth()
        elif risk_driver == "population_growth_existing":
            return PopulationGrowthExisting()
        elif risk_driver == "population_growth_new":
            return PopulationGrowthNew()
