from typing import ClassVar, List

from pydantic import BaseModel

from flood_adapt.objects.events.events import Event, Template
from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.forcing.forcing import (
    ForcingSource,
    ForcingType,
)
from flood_adapt.objects.forcing.time_frame import TimeFrame

__all__ = ["HurricaneEvent", "TranslationModel", "TimeFrame"]


class TranslationModel(BaseModel):
    """BaseModel describing the expected variables and data types for translation parameters of hurricane model."""

    eastwest_translation: us.UnitfulLength = us.UnitfulLength(
        value=0.0, units=us.UnitTypesLength.meters
    )
    northsouth_translation: us.UnitfulLength = us.UnitfulLength(
        value=0.0, units=us.UnitTypesLength.meters
    )


class HurricaneEvent(Event):
    """BaseModel describing the expected variables and data types for parameters of HurricaneEvent that extend the parent class Event.

    Attributes
    ----------
    name : str
        The name of the event.
    description :
        The description of the event. Defaults to "".
    time : TimeFrame
        The time frame of the event.
    template : Template
        The template of the event. Defaults to Template.Hurricane.
    mode : Mode
        The mode of the event. Defaults to Mode.single_event.
    rainfall_multiplier : float
        The rainfall multiplier of the event. Defaults to 1.0.
    forcings : dict[ForcingType, list[IForcing]]
        The forcings of the event.
    track_name : str
        The name of the hurricane track.
    """

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
