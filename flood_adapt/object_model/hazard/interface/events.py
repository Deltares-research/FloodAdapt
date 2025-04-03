import os
from abc import abstractmethod
from enum import Enum
from pathlib import Path
from typing import ClassVar, List

from pydantic import (
    Field,
)

from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    ForcingType,
    IForcing,
)
from flood_adapt.object_model.hazard.interface.models import TimeModel
from flood_adapt.object_model.interface.object_model import IObjectModel


class Mode(str, Enum):
    """Class describing the accepted input for the variable mode in Event."""

    single_event = "single_event"
    risk = "risk"


class Template(str, Enum):
    """Class describing the accepted input for the variable template in Event."""

    Synthetic = "Synthetic"
    Hurricane = "Hurricane"
    Historical = "Historical"

    @property
    def description(self) -> str:
        match self:
            case Template.Historical:
                return "Select a time period for a historic event. This method can use offshore wind and pressure fields for the selected time period to simulate nearshore water levels or download gauged waterlevels to perform a realistic simulation. These water levels are used together with rainfall and river discharge input to simulate flooding in the site area."
            case Template.Hurricane:
                return "Select a historical hurricane track from the hurricane database, and shift the track if desired."
            case Template.Synthetic:
                return "Customize a synthetic event by specifying the waterlevels, wind, rainfall and river discharges without being based on a historical event."
            case _:
                raise ValueError(f"Invalid event template: {self}")


class IEvent(IObjectModel):
    ALLOWED_FORCINGS: ClassVar[dict[ForcingType, List[ForcingSource]]]

    time: TimeModel
    template: Template
    mode: Mode = Mode.single_event

    forcings: dict[ForcingType, list[IForcing]] = Field(default_factory=dict)
    rainfall_multiplier: float = Field(default=1.0, ge=0)

    @abstractmethod
    def get_forcings(self) -> list[IForcing]: ...

    @abstractmethod
    def save_additional(self, output_dir: Path | str | os.PathLike) -> None: ...

    @abstractmethod
    def get_allowed_forcings(cls) -> dict[str, List[str]]: ...
