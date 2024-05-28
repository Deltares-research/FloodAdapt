from typing import Union

from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.hazard.event.eventset import EventSet
from flood_adapt.object_model.hazard.event.historical_hurricane import (
    HistoricalHurricane,
)
from flood_adapt.object_model.hazard.event.historical_nearshore import (
    HistoricalNearshore,
)
from flood_adapt.object_model.hazard.event.historical_offshore import HistoricalOffshore
from flood_adapt.object_model.hazard.event.synthetic import Synthetic
from flood_adapt.object_model.interface.events import Mode


class EventFactory:
    """EventFactory class object for creating event objects from templates

    Methods
    -------
    get_event(template)
        Returns event object based on template
    """

    @staticmethod
    def get_event(event_data: Union[str, dict]) -> Event:
        """Returns event object based on template name

        Parameters
        ----------
        event_data : Union[str, dict]
            Event data. If str, it is the path to the event file. If dict, it is the event data.

        Returns
        -------
        Event
            Event object
        """
        template = None
        if isinstance(event_data, dict):
            mode = event_data.mode
            if mode == Mode.single_event:
                template = event_data.template
        else:
            mode = Event.get_mode(event_data)
            if mode == Mode.single_event:
                template = Event.get_template(event_data)

        # Check template name and return object
        if mode == Mode.risk:
            event = EventSet()
        elif template == "Synthetic":
            event = Synthetic()
        elif template == "Historical_hurricane":
            event = HistoricalHurricane()
        elif template == "Historical_offshore":
            event = HistoricalOffshore()
        elif template == "Historical_nearshore":
            event = HistoricalNearshore()
    
        else:
            raise ValueError(f"Template '{template}' is not recognized.")

        if isinstance(event_data, dict):
            return event.load_dict(event_data)
        else:
            return event.load_file(event_data)

    @staticmethod
    def create_empty_event(template: str) -> Event:
        """Create an empty event object based on template name

        Parameters
        ----------
        template : str
            Template name

        Returns
        -------
        Event
            Event object
        """
        if template == "Synthetic":
            return Synthetic()
        elif template == "Historical_hurricane":
            return HistoricalHurricane()
        elif template == "Historical_offshore":
            return HistoricalOffshore()
        elif template == "Historical_nearshore":
            return HistoricalNearshore()
        else:
            raise ValueError(f"Template '{template}' is not recognized.")
