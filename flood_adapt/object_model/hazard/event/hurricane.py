from typing import ClassVar, List

from pydantic import BaseModel

from flood_adapt.object_model.hazard.event.template_event import Event
from flood_adapt.object_model.hazard.interface.events import Template
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    ForcingType,
)
from flood_adapt.object_model.io import unit_system as us


class TranslationModel(BaseModel):
    """BaseModel describing the expected variables and data types for translation parameters of hurricane model."""

    eastwest_translation: us.UnitfulLength = us.UnitfulLength(
        value=0.0, units=us.UnitTypesLength.meters
    )
    northsouth_translation: us.UnitfulLength = us.UnitfulLength(
        value=0.0, units=us.UnitTypesLength.meters
    )


class HurricaneEvent(Event):
    """BaseModel describing the expected variables and data types for parameters of HistoricalHurricane that extend the parent class Event."""

    ALLOWED_FORCINGS: ClassVar[dict[ForcingType, List[ForcingSource]]] = {
        ForcingType.RAINFALL: [
            ForcingSource.CONSTANT,
            ForcingSource.CSV,
            ForcingSource.SYNTHETIC,
            ForcingSource.TRACK,
        ],
        ForcingType.WIND: [ForcingSource.TRACK],
        ForcingType.WATERLEVEL: [ForcingSource.MODEL],
        ForcingType.DISCHARGE: [
            ForcingSource.CSV,
            ForcingSource.SYNTHETIC,
            ForcingSource.CONSTANT,
        ],
    }
    template: Template = Template.Hurricane
    hurricane_translation: TranslationModel = TranslationModel()
    track_name: str
