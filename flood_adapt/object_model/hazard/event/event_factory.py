from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.hazard.event.historical_hurricane import (
    HistoricalHurricane,
)
from flood_adapt.object_model.hazard.event.historical_nearshore import (
    HistoricalNearshore,
)
from flood_adapt.object_model.hazard.event.historical_offshore import HistoricalOffshore
from flood_adapt.object_model.hazard.event.synthetic import Synthetic
from flood_adapt.object_model.interface.events import Template


class EventFactory:
    """EventFactory class object for creating event objects from templates

    Methods
    -------
    get_event(template)
        Returns event object based on template
    """

    @staticmethod
    def get_event(template: Template) -> Event:
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
        if template == Template.SYNTHETIC:
            return Synthetic()
        elif template == Template.HURRICANE:
            return Hurricane()
        elif template == Template.OFFSHORE:
            return Offshore()
        elif template == Template.NEARSHORE:
            return Nearshore()
