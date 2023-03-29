# from flood_adapt.object_model.hazard.event.hurricane import Hurricane
# from flood_adapt.object_model.hazard.event.historical_offshore import HistoricalOffshore
from flood_adapt.object_model.hazard.event.historical_nearshore import (
    HistoricalNearshore,
)
from flood_adapt.object_model.hazard.event.synthetic import Synthetic


class EventFactory:
    @staticmethod
    def get_event(template: str):
        if template.lower() == "synthetic":
            return Synthetic()
        # elif template.lower() == "historical - hurricane":
        #     return Hurricane
        # elif template.lower() == "historical - forced by offshore wind and tide":
        #     return HistoricalOffshore
        elif template.lower() == "historical_nearshore":
            return HistoricalNearshore
