from typing import List

from flood_adapt.object_model.hazard.interface.events import (
    ForcingSource,
    ForcingType,
    IEvent,
    IEventModel,
)
from flood_adapt.object_model.interface.scenarios import IScenario


class SyntheticEventModel(IEventModel):  # add SurgeModel etc. that fit Synthetic event
    """BaseModel describing the expected variables and data types for parameters of Synthetic that extend the parent class Event."""

    ALLOWED_FORCINGS: dict[ForcingType, List[ForcingSource]] = {
        ForcingType.RAINFALL: [ForcingSource.CONSTANT, ForcingSource.SYNTHETIC],
        ForcingType.WIND: [ForcingSource.CONSTANT, ForcingSource.SYNTHETIC],
        ForcingType.WATERLEVEL: [ForcingSource.SYNTHETIC, ForcingSource.CSV],
        ForcingType.DISCHARGE: [ForcingSource.CONSTANT, ForcingSource.SYNTHETIC],
    }


class SyntheticEvent(IEvent):
    MODEL_TYPE = SyntheticEventModel

    attrs: SyntheticEventModel

    def process(self, scenario: IScenario = None):
        """Synthetic events do not require any processing."""
        return
