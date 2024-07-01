from abc import ABC, abstractmethod

from flood_adapt.object_model.hazard.new_events.new_event_models import (
    EventSetModel,
    HurricaneEventModel,
    IEventModel,
)
from flood_adapt.object_model.interface.scenarios import ScenarioModel


class IEvent(ABC):
    attrs: IEventModel

    @abstractmethod
    def process(self, scenario: ScenarioModel):
        """
        Process the event.

        - Read event- & scenario models to see what forcings are needed
        - Compute forcing data (via synthetic functions or running offshore)
        - Write output to self.forcings
        """
        pass


class HurricaneEvent(IEvent):
    attrs: HurricaneEventModel


class EventSet(IEvent):
    attrs: EventSetModel
