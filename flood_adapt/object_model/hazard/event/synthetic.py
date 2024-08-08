from typing import ClassVar, List

from flood_adapt.object_model.hazard.event.forcing.forcing_factory import ForcingFactory
from flood_adapt.object_model.hazard.interface.events import (
    ForcingSource,
    ForcingType,
    IEvent,
    IEventModel,
)
from flood_adapt.object_model.hazard.interface.models import Mode, Template, TimeModel
from flood_adapt.object_model.interface.scenarios import IScenario


class SyntheticEventModel(IEventModel):  # add SurgeModel etc. that fit Synthetic event
    """BaseModel describing the expected variables and data types for parameters of Synthetic that extend the parent class Event."""

    ALLOWED_FORCINGS: ClassVar[dict[ForcingType, List[ForcingSource]]] = {
        ForcingType.RAINFALL: [ForcingSource.CONSTANT, ForcingSource.SYNTHETIC],
        ForcingType.WIND: [ForcingSource.CONSTANT, ForcingSource.SYNTHETIC],
        ForcingType.WATERLEVEL: [ForcingSource.SYNTHETIC, ForcingSource.CSV],
        ForcingType.DISCHARGE: [ForcingSource.CONSTANT, ForcingSource.SYNTHETIC],
    }

    def default(self):
        """Set default values for Synthetic event."""
        return SyntheticEventModel(
            name="Synthetic Event",
            time=TimeModel(),
            template=Template.Synthetic,
            mode=Mode.single_event,
            forcings={
                ForcingType.RAINFALL: ForcingFactory.get_default_forcing(
                    ForcingType.RAINFALL, ForcingSource.SYNTHETIC
                ),
                ForcingType.WIND: ForcingFactory.get_default_forcing(
                    ForcingType.WIND, ForcingSource.SYNTHETIC
                ),
                ForcingType.WATERLEVEL: ForcingFactory.get_default_forcing(
                    ForcingType.WATERLEVEL, ForcingSource.SYNTHETIC
                ),
                ForcingType.DISCHARGE: ForcingFactory.get_default_forcing(
                    ForcingType.DISCHARGE, ForcingSource.SYNTHETIC
                ),
            },
        )


class SyntheticEvent(IEvent):
    MODEL_TYPE = SyntheticEventModel

    attrs: SyntheticEventModel

    def process(self, scenario: IScenario = None):
        """Synthetic events do not require any processing."""
        return
