from abc import ABC, abstractmethod
from typing import List

from flood_adapt.object_model.interface.events import EventModel, IForcing


class Event(ABC):
    attrs: EventModel
    forcings: List[IForcing]

    @abstractmethod
    def preprocess(self):
        """
        Preprocess the event.

        - Read eventmodel to see what forcings are needed
        - Compute forcing data (via synthetic functions or running offshore)
        - Write to forcing files.
        """
        pass
