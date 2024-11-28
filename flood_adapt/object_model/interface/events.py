import os
from abc import abstractmethod
from pathlib import Path
from typing import Any, ClassVar, List, Optional, Type, TypeVar

from pydantic import (
    Field,
)

from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    ForcingType,
    IForcing,
)
from flood_adapt.object_model.hazard.interface.models import (
    Mode,
    Template,
    TimeModel,
)
from flood_adapt.object_model.interface.object_model import IObject, IObjectModel
from flood_adapt.object_model.interface.path_builder import (
    ObjectDir,
)
from flood_adapt.object_model.io import unit_system as us


class IEventModel(IObjectModel):
    ALLOWED_FORCINGS: ClassVar[dict[ForcingType, List[ForcingSource]]]

    time: TimeModel
    template: Template
    mode: Mode
    water_level_offset: us.UnitfulLength = us.UnitfulLength(
        value=0, units=us.UnitTypesLength.meters
    )

    forcings: dict[ForcingType, Any] = Field(default_factory=dict)


T_IEVENT_MODEL = TypeVar("T_IEVENT_MODEL", bound=IEventModel)


class IEvent(IObject[T_IEVENT_MODEL]):
    _attrs_type: Type[T_IEVENT_MODEL]

    dir_name = ObjectDir.event
    display_name = "Event"

    _site = None

    @abstractmethod
    def get_forcings(self) -> list[IForcing]: ...

    @abstractmethod
    def save_additional(self, output_dir: Path | str | os.PathLike) -> None: ...

    @abstractmethod
    def preprocess(self, output_dir: Path): ...

    @abstractmethod
    def plot_forcing(
        self,
        forcing_type: ForcingType,
        units: Optional[
            us.UnitTypesLength
            | us.UnitTypesIntensity
            | us.UnitTypesDischarge
            | us.UnitTypesVelocity
        ] = None,
        **kwargs,
    ) -> str | None: ...

    @abstractmethod
    def plot_waterlevel(
        self, units: Optional[us.UnitTypesLength] = None, **kwargs
    ) -> str: ...

    @abstractmethod
    def plot_rainfall(
        self,
        units: Optional[us.UnitTypesIntensity] = None,
        rainfall_multiplier: Optional[float] = None,
        **kwargs,
    ) -> str | None: ...

    @abstractmethod
    def plot_discharge(
        self, units: Optional[us.UnitTypesDischarge] = None, **kwargs
    ) -> str: ...

    @abstractmethod
    def plot_wind(
        self,
        velocity_units: Optional[us.UnitTypesVelocity] = None,
        direction_units: Optional[us.UnitTypesDirection] = None,
        **kwargs,
    ) -> str: ...
