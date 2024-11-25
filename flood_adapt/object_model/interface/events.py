import os
from abc import abstractmethod
from pathlib import Path
from typing import Any, ClassVar, List, Optional, Type, TypeVar

from pydantic import (
    Field,
    field_serializer,
    model_validator,
)

import flood_adapt.object_model.io.unitfulvalue as uv
from flood_adapt.object_model.hazard.event.forcing.forcing_factory import ForcingFactory
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


class IEventModel(IObjectModel):
    ALLOWED_FORCINGS: ClassVar[dict[ForcingType, List[ForcingSource]]]

    time: TimeModel
    template: Template
    mode: Mode
    water_level_offset: uv.UnitfulLength = uv.UnitfulLength(
        value=0, units=uv.UnitTypesLength.meters
    )

    forcings: dict[ForcingType, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    def create_forcings(self):
        if "forcings" in self:
            forcings = {}
            for ftype, forcing_attrs in self["forcings"].items():
                if isinstance(forcing_attrs, IForcing):
                    # forcing_attrs is already a forcing object
                    forcings[ftype] = forcing_attrs
                elif (
                    isinstance(forcing_attrs, dict)
                    and "_type" in forcing_attrs
                    and "_source" in forcing_attrs
                ):
                    # forcing_attrs is a dict with forcing attributes
                    forcings[ftype] = ForcingFactory.load_dict(forcing_attrs)
                else:
                    # forcing_attrs is a dict with sub-forcing attributes. Currently only used for discharge forcing
                    for name, sub_forcing in forcing_attrs.items():
                        if ftype not in forcings:
                            forcings[ftype] = {}

                        if isinstance(sub_forcing, IForcing):
                            forcings[ftype][name] = sub_forcing
                        else:
                            forcings[ftype][name] = ForcingFactory.load_dict(
                                sub_forcing
                            )
            self["forcings"] = forcings
        return self

    @model_validator(mode="after")
    def validate_forcings(self):
        def validate_concrete_forcing(concrete_forcing):
            _type = concrete_forcing._type
            _source = concrete_forcing._source

            # Check type
            if _type not in self.__class__.ALLOWED_FORCINGS:
                allowed_types = ", ".join(
                    t.value for t in self.__class__.ALLOWED_FORCINGS.keys()
                )
                raise ValueError(
                    f"Forcing type {_type.value} is not allowed. Allowed types are: {allowed_types}"
                )

            # Check source
            if _source not in self.__class__.ALLOWED_FORCINGS[_type]:
                allowed_sources = ", ".join(
                    s.value for s in self.__class__.ALLOWED_FORCINGS[_type]
                )
                raise ValueError(
                    f"Forcing source {_source.value} is not allowed for forcing type {_type.value}. "
                    f"Allowed sources are: {allowed_sources}"
                )

        for concrete_forcing in self.forcings.values():
            if concrete_forcing is None:
                continue

            if isinstance(concrete_forcing, dict):
                for _, _concrete_forcing in concrete_forcing.items():
                    validate_concrete_forcing(_concrete_forcing)
            else:
                validate_concrete_forcing(concrete_forcing)

        return self

    @field_serializer("forcings")
    @classmethod
    def serialize_forcings(
        cls, value: dict[ForcingType, IForcing | dict[str, IForcing]]
    ) -> dict[str, dict[str, Any]]:
        dct = {}
        for ftype, forcing in value.items():
            if not forcing:
                continue
            if isinstance(forcing, IForcing):
                dct[ftype.value] = forcing.model_dump(exclude_none=True)
            else:
                dct[ftype.value] = {
                    name: forcing.model_dump(exclude_none=True)
                    for name, forcing in forcing.items()
                }
        return dct

    @classmethod
    def get_allowed_forcings(cls) -> dict[str, List[str]]:
        return {k.value: [s.value for s in v] for k, v in cls.ALLOWED_FORCINGS.items()}

    @classmethod
    def default(cls) -> "IEventModel":
        """Return the default event model."""
        ...


T = TypeVar("T", bound=IEventModel)


class IEvent(IObject[T]):
    MODEL_TYPE: Type[T]
    dir_name = ObjectDir.event
    display_name = "Event"

    attrs: T
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
            uv.UnitTypesLength
            | uv.UnitTypesIntensity
            | uv.UnitTypesDischarge
            | uv.UnitTypesVelocity
        ] = None,
        **kwargs,
    ) -> str | None: ...

    @abstractmethod
    def plot_waterlevel(
        self, units: Optional[uv.UnitTypesLength] = None, **kwargs
    ) -> str: ...

    @abstractmethod
    def plot_rainfall(
        self,
        units: Optional[uv.UnitTypesIntensity] = None,
        rainfall_multiplier: Optional[float] = None,
        **kwargs,
    ) -> str | None: ...

    @abstractmethod
    def plot_discharge(
        self, units: Optional[uv.UnitTypesDischarge] = None, **kwargs
    ) -> str: ...

    @abstractmethod
    def plot_wind(
        self,
        velocity_units: Optional[uv.UnitTypesVelocity] = None,
        direction_units: Optional[uv.UnitTypesDirection] = None,
        **kwargs,
    ) -> str: ...
