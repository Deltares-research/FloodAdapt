# from flood_adapt.object_model.hazard.event.hurricane import Hurricane
# from flood_adapt.object_model.hazard.event.historical_offshore import HistoricalOffshore
from flood_adapt.object_model.hazard.event.historical_nearshore import (
    HistoricalNearshore,
)
from .synthetic import Synthetic
from flood_adapt.object_model.hazard.event.historical_offshore import HistoricalOffshore
from flood_adapt.object_model.hazard.event.synthetic import Synthetic


class EventFactory:
    """EventFactory class object for creating event objects from templates

    Methods
    -------
    get_event(template)
        Returns event object based on template
    """

    @staticmethod
    def get_event(template: str) -> Event:
        """Returns event object based on template name

        Parameters
        ----------
        template : str
            Template name

        Returns
        -------
        Event
            Event object
        """

        # Check template name and return object
        if template == "Synthetic":
            return Synthetic()
        # elif template.lower() == "Hurricane":
        #     return Hurricane
        # elif template.lower() == "Historical_offshore":
        #     return HistoricalOffshore
        elif template == "Historical_nearshore":
            return HistoricalNearshore

        # TODO: Add historical offshore
