# from flood_adapt.object_model.hazard.event.hurricane import Hurricane
from flood_adapt.object_model.hazard.event.historical_nearshore import (
    HistoricalNearshore,
)
from flood_adapt.object_model.hazard.event.historical_offshore import HistoricalOffshore
from flood_adapt.object_model.hazard.event.synthetic import Synthetic


class EventFactory:
    @staticmethod
    def get_event(template: str):
        if template == "Synthetic":
            return Synthetic()
        # elif template == "Hurricane":
        #     return Hurricane
        elif template == "Historical_offshore":
            return HistoricalOffshore
        elif template == "Historical_nearshore":
            return HistoricalNearshore
