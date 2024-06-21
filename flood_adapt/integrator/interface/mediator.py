from abc import ABC, abstractmethod
from typing import List

from flood_adapt.integrator.interface.model_adapter import IAdapter
from flood_adapt.object_model.interface.scenarios import IScenario


class IMediator(ABC):
    models: List[IAdapter]

    def register(self, model: IAdapter):
        self.models.append(model)
        model._mediator = self

    def deregister(self, model: IAdapter):
        model._mediator = None
        self.models.remove(model)

    @abstractmethod
    def run_scenario(self, scenario: IScenario):
        pass
