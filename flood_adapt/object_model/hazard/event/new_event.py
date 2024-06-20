from abc import ABC, abstractmethod

from flood_adapt.object_model.hazard.event.new_event_models import (
    EventSetModel,
    HistoricalEventModel,
    HurricaneEventModel,
    IEventModel,
    SyntheticEventModel,
)


class IEvent(ABC):
    attrs: IEventModel

    @abstractmethod
    def process(self):
        """
        Process the event.

        - Read eventmodel to see what forcings are needed
        - Compute forcing data (via synthetic functions or running offshore)
        - Write output to self.forcings
        """
        pass


class SyntheticEvent(IEvent):
    attrs: SyntheticEventModel


class HistoricalEvent(IEvent):
    attrs: HistoricalEventModel

    def process(self):
        # if *FromModel in forcings, run offshore sfincs model
        pass

    def download_data(self):
        # download data from external sources
        pass


class HurricaneEvent(IEvent):
    attrs: HurricaneEventModel

    def process(self):
        # if *FromModel in forcings, run offshore sfincs model
        pass


class EventSet(IEvent):
    attrs: EventSetModel
