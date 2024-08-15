import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar

import pandas as pd
import tomli
from pydantic import BaseModel

from flood_adapt.log import FloodAdaptLogging
from flood_adapt.object_model.hazard.interface.models import (
    ForcingSource,
    ForcingType,
)


class IForcing(BaseModel, ABC):
    """BaseModel describing the expected variables and data types for forcing parameters of hazard model."""

    _type: ClassVar[ForcingType]
    _source: ClassVar[ForcingSource]
    _logger: ClassVar[logging.Logger] = FloodAdaptLogging.getLogger(__name__)

    @classmethod
    def load_file(cls, path: str | os.PathLike):
        with open(path, mode="rb") as fp:
            toml_data = tomli.load(fp)
        return cls.load_dict(toml_data)

    @classmethod
    def load_dict(cls, attrs):
        return cls.model_validate(attrs)

    def get_data(self, strict: bool = True, **kwargs: Any) -> pd.DataFrame:
        """If applicable, return the forcing/timeseries data as a (pd.DataFrame | xr.DataSet | arrayLike) data structure.

        Args:
            raise (bool, optional): If True, raise an error if the data cannot be returned. Defaults to True.

        The default implementation is to return None, if it makes sense to return an arrayLike datastructure, return it, otherwise return None.
        """
        return

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Override the default model_dump to include class variables `_type` and `_source`."""
        data = super().model_dump(**kwargs)
        # Add the class variables to the serialized data
        data["_type"] = self._type.value if self._type else None
        data["_source"] = self._source.value if self._source else None
        return data

    @abstractmethod
    def default() -> "IForcing":
        """Return the default for this forcing."""
        ...


class IDischarge(IForcing):
    _type: ClassVar[ForcingType] = ForcingType.DISCHARGE


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
