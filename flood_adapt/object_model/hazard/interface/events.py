import os
from typing import Any, ClassVar, List, Optional

import tomli
import tomli_w
from pydantic import (
    BaseModel,
    Field,
    field_serializer,
    model_validator,
)

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
from flood_adapt.object_model.interface.database_user import IDatabaseUser
from flood_adapt.object_model.interface.scenarios import IScenario


class IEventModel(BaseModel):
    ALLOWED_FORCINGS: ClassVar[dict[ForcingType, List[ForcingSource]]]

    name: str
    description: Optional[str] = None
    time: TimeModel
    template: Template
    mode: Mode

    forcings: dict[ForcingType, IForcing] = Field(default_factory=dict)

    @model_validator(mode="before")
    def create_forcings(self):
        if "forcings" in self:
            forcings = {}
            for ftype, forcing_attrs in self["forcings"].items():
                if isinstance(forcing_attrs, IForcing):
                    forcings[ftype] = forcing_attrs
                else:
                    forcings[ftype] = ForcingFactory.load_dict(forcing_attrs)
            self["forcings"] = forcings
        return self

    @model_validator(mode="after")
    def validate_forcings(self):
        for concrete_forcing in self.forcings.values():
            if concrete_forcing is None:
                continue
            _type = concrete_forcing._type
            _source = concrete_forcing._source

            # Check type
            if concrete_forcing._type not in self.__class__.ALLOWED_FORCINGS:
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
        return self

    @field_serializer("forcings")
    @classmethod
    def serialize_forcings(
        cls, value: dict[ForcingType, IForcing]
    ) -> dict[str, dict[str, Any]]:
        return {
            type.name: forcing.model_dump(exclude_none=True)
            for type, forcing in value.items()
            if type
        }


class IEvent(IDatabaseUser):
    MODEL_TYPE: ClassVar[IEventModel]

    attrs: IEventModel

    @classmethod
    def load_file(cls, path: str | os.PathLike):
        with open(path, "rb") as file:
            attrs = tomli.load(file)
        return cls.load_dict(attrs)

    @classmethod
    def load_dict(cls, data: dict[str, Any]):
        obj = cls()
        obj.attrs = cls.MODEL_TYPE.model_validate(data)
        return obj

    def save(self, path: str | os.PathLike):
        with open(path, "wb") as f:
            tomli_w.dump(self.attrs.model_dump(exclude_none=True), f)

    def process(self, scenario: IScenario):
        """
        Process the event to generate forcing data.

        This is the simplest implementation of the process method. For more complicated events, overwrite this method in the subclass.

        - Read event- & scenario models to see what forcings are needed
        - Compute forcing data (via synthetic functions or running offshore)
        - Write output as pd.DataFrame to self.forcing_data[ForcingType]
        """
        for forcing in self.attrs.forcings.values():
            forcing.process(self.attrs.time, self.database.site)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        _self = self.attrs.model_dump(
            exclude=["name", "description"], exclude_none=True
        )
        _other = other.attrs.model_dump(
            exclude=["name", "description"], exclude_none=True
        )
        return _self == _other
