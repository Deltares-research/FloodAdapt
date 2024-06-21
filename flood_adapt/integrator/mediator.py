from typing import List

from flood_adapt.dbs_controller import Database
from flood_adapt.integrator.interface.hazard_adapter import IHazardAdapter
from flood_adapt.integrator.interface.impact_adapter import IImpactAdapter
from flood_adapt.integrator.interface.mediator import IMediator
from flood_adapt.integrator.interface.model_adapter import IAdapter
from flood_adapt.object_model.interface.scenarios import IScenario


class Mediator(IMediator):
    def __init__(self, models: List[IAdapter]):
        for model in models:
            self.register(model)

    def run_scenario(self, scenario: IScenario):
        for hazard_model in [m for m in self.models if isinstance(m, IHazardAdapter)]:
            hazard_model.run(scenario)
        scenario.attrs.hazards_completed = True
        Database().scenarios.save(scenario)

        for impact_model in [m for m in self.models if isinstance(m, IImpactAdapter)]:
            impact_model.run(scenario)
        scenario.attrs.impacts_completed = True
        Database().scenarios.save(scenario)
