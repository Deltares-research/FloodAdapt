from flood_adapt.object_model.hazard.new_events.new_event import IEvent
from flood_adapt.object_model.hazard.new_events.new_event_models import (
    SyntheticEventModel,
)
from flood_adapt.object_model.interface.scenarios import ScenarioModel


class SyntheticEvent(IEvent):
    attrs: SyntheticEventModel

    def process(self, scenario: ScenarioModel):
        """Synthetic events do not require any processing."""
        pass
