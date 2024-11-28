import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar, Optional

import pandas as pd
import tomli
from pydantic import BaseModel, field_serializer

from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.object_model.hazard.event.timeseries import REFERENCE_TIME
from flood_adapt.object_model.hazard.interface.models import (
    ForcingSource,
    ForcingType,
)
from flood_adapt.object_model.interface.site import RiverModel
from flood_adapt.object_model.io import unit_system as us


class IForcing(BaseModel, ABC):
    """BaseModel describing the expected variables and data types for forcing parameters of hazard model."""

    class Config:
        arbitrary_types_allowed = True

    _type: ClassVar[ForcingType]
    _source: ClassVar[ForcingSource]
    logger: ClassVar[logging.Logger] = FloodAdaptLogging.getLogger(__name__)

    @classmethod
    def load_file(cls, path: Path):
        with open(path, mode="rb") as fp:
            toml_data = tomli.load(fp)
        return cls.load_dict(toml_data)

    @classmethod
    def load_dict(cls, attrs):
        return cls.model_validate(attrs)

    def get_data(
        self,
        t0: Optional[datetime] = None,
        t1: Optional[datetime] = None,
        strict: bool = True,
        **kwargs: Any,
    ) -> Optional[pd.DataFrame]:
        """If applicable, return the forcing/timeseries data as a (pd.DataFrame | xr.DataSet | arrayLike) data structure.

        Args:
            t0 (datetime, optional): Start time of the data.
            t1 (datetime, optional): End time of the data.
            strict (bool, optional): If True, raise an error if the data cannot be returned. Defaults to True.

        The default implementation is to return None, if it makes sense to return a dataframe-like datastructure, return it, otherwise return None.
        """
        return None

    def parse_time(
        self,
        t0: Optional[datetime | us.UnitfulTime],
        t1: Optional[datetime | us.UnitfulTime],
    ) -> tuple[datetime, datetime]:
        """
        Parse the time inputs to ensure they are datetime objects.

        If the inputs are us.UnitfulTime objects (Synthetic), convert them to datetime objects using the reference time as the base time.
        """
        if t0 is None:
            t0 = REFERENCE_TIME
        elif isinstance(t0, us.UnitfulTime):
            t0 = REFERENCE_TIME + t0.to_timedelta()

        if t1 is None:
            t1 = (
                t0
                + us.UnitfulTime(value=1, units=us.UnitTypesTime.hours).to_timedelta()
            )
        elif isinstance(t1, us.UnitfulTime):
            t1 = t0 + t1.to_timedelta()
        return t0, t1

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Override the default model_dump to include class variables `_type` and `_source`."""
        data = super().model_dump(**kwargs)
        # Add the class variables to the serialized data
        data["_type"] = self._type.value if self._type else None
        data["_source"] = self._source.value if self._source else None
        return data

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        """Save additional data of the forcing."""
        return

    @classmethod
    @abstractmethod
    def default(cls) -> "IForcing":
        """Return the default for this forcing."""
        ...

    @field_serializer("path", check_fields=False)
    @classmethod
    def serialize_path(cls, value: Path) -> str:
        """Serialize filepath-like fields."""
        return str(value)


class IDischarge(IForcing):
    _type: ClassVar[ForcingType] = ForcingType.DISCHARGE
    river: RiverModel


class IRainfall(IForcing):
    _type: ClassVar[ForcingType] = ForcingType.RAINFALL


class IWind(IForcing):
    _type: ClassVar[ForcingType] = ForcingType.WIND


class IWaterlevel(IForcing):
    _type: ClassVar[ForcingType] = ForcingType.WATERLEVEL


class IForcingFactory:
    @classmethod
    @abstractmethod
    def load_file(cls, toml_file: Path) -> IForcing:
        pass

    @classmethod
    @abstractmethod
    def load_dict(cls, attrs: dict[str, Any]) -> IForcing:
        pass
