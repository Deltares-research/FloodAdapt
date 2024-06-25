from abc import ABC, abstractmethod

from flood_adapt.object_model.hazard.event.new_event_models import (
    EventSetModel,
    HurricaneEventModel,
    IEventModel,
    SyntheticEventModel,
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


class SyntheticEvent(IEvent):
    attrs: SyntheticEventModel


class HurricaneEvent(IEvent):
    attrs: HurricaneEventModel

    def process(self):
        # if *FromModel in forcings, run offshore sfincs model
        pass


class EventSet(IEvent):
    attrs: EventSetModel
