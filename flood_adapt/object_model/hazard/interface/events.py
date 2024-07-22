import os
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, List, Optional

import tomli
from pydantic import BaseModel, Field, field_validator, model_validator

from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    ForcingType,
    IForcing,
)
from flood_adapt.object_model.interface.scenarios import IScenario

DEFAULT_START_TIME = datetime(year=2020, month=1, day=1, hour=0)
DEFAULT_END_TIME = datetime(year=2020, month=1, day=1, hour=3)


class Mode(str, Enum):
    """Class describing the accepted input for the variable mode in Event."""

    single_event = "single_event"
    risk = "risk"


class Template(str, Enum):
    """Class describing the accepted input for the variable template in Event."""

    Synthetic = "Synthetic"
    Hurricane = "Historical_hurricane"
    Historical_nearshore = "Historical_nearshore"
    Historical_offshore = "Historical_offshore"
    Historical = "Historical"


class TimeModel(BaseModel):
    start_time: datetime = DEFAULT_START_TIME
    end_time: datetime = DEFAULT_END_TIME
    time_step: timedelta = timedelta(minutes=10)

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def try_parse_datetime(cls, value: str | datetime) -> datetime:
        SUPPORTED_DATETIME_FORMATS = [
            "%Y%m%d %H%M%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S.%f%z",
        ]
        if not isinstance(value, datetime):
            for fmt in SUPPORTED_DATETIME_FORMATS:
                try:
                    value = datetime.strptime(value, fmt)
                    break
                except Exception:
                    pass

        if not isinstance(value, datetime):
            raise ValueError(
                f"Could not parse start time: {value}. Supported formats are {', '.join(SUPPORTED_DATETIME_FORMATS)}"
            )
        return value


def default_forcings() -> dict[ForcingType, list[None]]:
    return {
        ForcingType.WATERLEVEL: None,
        ForcingType.WIND: None,
        ForcingType.RAINFALL: None,
        ForcingType.DISCHARGE: None,
    }


class IEventModel(BaseModel):
    ALLOWED_FORCINGS: dict[ForcingType, List[ForcingSource]] = Field(
        default_factory=default_forcings, frozen=True
    )

    name: str
    description: Optional[str] = None
    time: TimeModel
    template: Template
    mode: Mode

    forcings: dict[ForcingType, IForcing] = Field(default_factory=default_forcings)

    @model_validator(mode="after")
    def validate_forcings(self):
        for concrete_forcing in self.forcings.values():
            if concrete_forcing is None:
                continue
            _type = concrete_forcing._type
            _source = concrete_forcing._source
            # Check type
            if concrete_forcing._type not in type(self).ALLOWED_FORCINGS:
                raise ValueError(
                    f"Forcing {_type} not in allowed forcings {type(self).ALLOWED_FORCINGS}"
                )

            # Check source
            if _source not in type(self).ALLOWED_FORCINGS[_type]:
                raise ValueError(
                    f"Forcing {concrete_forcing} not allowed for forcing category {_type}. Only {', '.join(type(self).ALLOWED_FORCINGS[_type].__name__)} are allowed"
                )
        return self


class IEvent(ABC):
    MODEL_TYPE: IEventModel

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

    def process(self, scenario: IScenario):
        """
        Process the event to generate forcing data.

        This is the simplest implementation of the process method. For more complicated events, overwrite this method in the subclass.

        - Read event- & scenario models to see what forcings are needed
        - Compute forcing data (via synthetic functions or running offshore)
        - Write output as pd.DataFrame to self.forcing_data[ForcingType]
        """
        for forcing in self.attrs.forcings.values():
            forcing.process(self.attrs.time)
            self.forcing_data[forcing._type] = forcing.get_data()


class IEventFactory:
    @abstractmethod
    def get_event_class(self, template: Template) -> IEvent:
        pass

    @abstractmethod
    def get_template(self, filepath: Path) -> Template:
        pass

    @abstractmethod
    def get_mode(self, filepath: Path) -> Mode:
        pass

    @abstractmethod
    def load_file(self, toml_file: Path) -> IEvent:
        pass

    @abstractmethod
    def load_dict(self, attrs: dict[str, Any]) -> IEvent:
        pass
