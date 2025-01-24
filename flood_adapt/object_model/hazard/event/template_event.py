import os
from pathlib import Path
from typing import Any, List, Optional, Type, TypeVar

from pydantic import field_serializer, field_validator, model_validator

from flood_adapt.object_model.hazard.forcing.forcing_factory import ForcingFactory
from flood_adapt.object_model.hazard.interface.events import (
    ForcingSource,
    ForcingType,
    IEvent,
    IEventModel,
    IForcing,
)


class EventModel(IEventModel):
    @staticmethod
    def _parse_forcing_from_dict(
        forcing_attrs: dict[str, Any] | IForcing,
        ftype: Optional[ForcingType] = None,
        fsource: Optional[ForcingSource] = None,
    ) -> IForcing:
        if isinstance(forcing_attrs, IForcing):
            # forcing_attrs is already a forcing object
            return forcing_attrs
        elif isinstance(forcing_attrs, dict):
            # forcing_attrs is a dict with valid forcing attributes
            if "type" not in forcing_attrs and ftype:
                forcing_attrs["type"] = ftype
            if "source" not in forcing_attrs and fsource:
                forcing_attrs["source"] = fsource

            return ForcingFactory.load_dict(forcing_attrs)
        else:
            raise ValueError(
                f"Invalid forcing attributes: {forcing_attrs}. "
                "Forcings must be one of:\n"
                "1. Instance of IForcing\n"
                "2. dict with the keys `type` (ForcingType), `source` (ForcingSource) specifying the class, and with valid forcing attributes for that class."
            )

    @field_validator("forcings", mode="before")
    @classmethod
    def create_forcings(
        cls, value: dict[str, list[dict[str, Any]]]
    ) -> dict[ForcingType, list[IForcing]]:
        forcings = {}
        for ftype, forcing_list in value.items():
            ftype = ForcingType(ftype)
            forcings[ftype] = [
                EventModel._parse_forcing_from_dict(forcing, ftype)
                for forcing in forcing_list
            ]
        return forcings

    @model_validator(mode="after")
    def validate_forcings(self):
        def validate_concrete_forcing(concrete_forcing):
            type = concrete_forcing.type
            source = concrete_forcing.source

            # Check type
            if type not in self.__class__.ALLOWED_FORCINGS:
                allowed_types = ", ".join(
                    t.value for t in self.__class__.ALLOWED_FORCINGS.keys()
                )
                raise ValueError(
                    f"Forcing type {type.value} is not allowed. Allowed types are: {allowed_types}"
                )

            # Check source
            if source not in self.__class__.ALLOWED_FORCINGS[type]:
                allowed_sources = ", ".join(
                    s.value for s in self.__class__.ALLOWED_FORCINGS[type]
                )
                raise ValueError(
                    f"Forcing source {source.value} is not allowed for forcing type {type.value}. "
                    f"Allowed sources are: {allowed_sources}"
                )

        # Validate forcings
        for _, concrete_forcings in self.forcings.items():
            for concrete_forcing in concrete_forcings:
                validate_concrete_forcing(concrete_forcing)

        return self

    @field_serializer("forcings")
    @classmethod
    def serialize_forcings(
        cls, value: dict[ForcingType, List[IForcing]]
    ) -> dict[str, List[dict[str, Any]]]:
        dct = {}
        for ftype, forcing_list in value.items():
            dct[ftype.value] = [
                forcing.model_dump(exclude_none=True) for forcing in forcing_list
            ]
        return dct

    @classmethod
    def get_allowed_forcings(cls) -> dict[str, List[str]]:
        return {k.value: [s.value for s in v] for k, v in cls.ALLOWED_FORCINGS.items()}


T_EVENT_MODEL = TypeVar("T_EVENT_MODEL", bound=EventModel)


class Event(IEvent[T_EVENT_MODEL]):
    _attrs_type: Type[T_EVENT_MODEL]

    def get_forcings(self) -> list[IForcing]:
        forcings = []
        for forcing_list in self.attrs.forcings.values():
            forcings.extend(forcing_list)
        return forcings

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        for forcing in self.get_forcings():
            forcing.save_additional(output_dir)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        _self = self.attrs.model_dump(
            exclude={"name", "description"}, exclude_none=True
        )
        _other = other.attrs.model_dump(
            exclude={"name", "description"}, exclude_none=True
        )
        return _self == _other
