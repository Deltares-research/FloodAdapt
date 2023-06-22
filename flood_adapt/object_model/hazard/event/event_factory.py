from .event import Event
from .historical_hurricane import (
    HistoricalHurricane,
)
from .historical_nearshore import (
    HistoricalNearshore,
)
from .synthetic import Synthetic


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
            return Synthetic
        elif template == "Historical_hurricane":
            return HistoricalHurricane
        elif template == "Historical_nearshore":
            return HistoricalNearshore

        # TODO: Add historical offshore
