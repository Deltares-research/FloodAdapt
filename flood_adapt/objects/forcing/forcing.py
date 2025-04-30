import logging
import os
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar, List, Type

import tomli
from pydantic import BaseModel, field_serializer

from flood_adapt.config.sfincs import RiverModel
from flood_adapt.misc.log import FloodAdaptLogging


### ENUMS ###
class ForcingType(str, Enum):
    """Enum class for the different types of forcing parameters.

    Attributes
    ----------
    RAINFALL : The type of forcing parameter for rainfall.
    WIND : The type of forcing parameter for wind.
    DISCHARGE : The type of forcing parameter for discharge.
    WATERLEVEL : The type of forcing parameter for water level.
    """

    WIND = "WIND"
    RAINFALL = "RAINFALL"
    DISCHARGE = "DISCHARGE"
    WATERLEVEL = "WATERLEVEL"


class ForcingSource(str, Enum):
    """Enum class for the different sources of forcing parameters."""

    MODEL = "MODEL"  # 'our' hindcast/ sfincs offshore model
    TRACK = "TRACK"  # 'our' hindcast/ sfincs offshore model + (shifted) hurricane
    CSV = "CSV"  # user provided csv file
    NETCDF = "NETCDF"  # user provided netcdf file

    SYNTHETIC = "SYNTHETIC"  # synthetic data
    CONSTANT = "CONSTANT"  # synthetic data

    GAUGED = "GAUGED"  # data downloaded from a gauge
    METEO = "METEO"  # external hindcast data

    NONE = "NONE"  # no forcing data


class IForcing(BaseModel, ABC):
    """BaseModel describing the expected variables and data types for forcing parameters of hazard model."""

    class Config:
        arbitrary_types_allowed = True

    type: ForcingType
    source: ForcingSource
    logger: ClassVar[logging.Logger] = FloodAdaptLogging.getLogger("Forcing")

    @classmethod
    def load_file(cls, path: Path):
        with open(path, mode="rb") as fp:
            toml_data = tomli.load(fp)
        return cls.load_dict(toml_data)

    @classmethod
    def load_dict(cls, attrs):
        return cls.model_validate(attrs)

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Override the default model_dump to include class variables `type` and `source`."""
        data = super().model_dump(**kwargs)
        data.update({"type": self.type, "source": self.source})
        return data

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        """Save additional data of the forcing."""
        return

    @field_serializer("path", check_fields=False)
    @classmethod
    def serialize_path(cls, value: Path) -> str:
        """Serialize filepath-like fields by saving only the filename. It is assumed that the file will be saved in the same directory."""
        return value.name


class IDischarge(IForcing):
    type: ForcingType = ForcingType.DISCHARGE
    river: RiverModel


class IRainfall(IForcing):
    type: ForcingType = ForcingType.RAINFALL


class IWind(IForcing):
    type: ForcingType = ForcingType.WIND


class IWaterlevel(IForcing):
    type: ForcingType = ForcingType.WATERLEVEL


class IForcingFactory:
    @classmethod
    @abstractmethod
    def load_file(cls, toml_file: Path) -> IForcing:
        """Create a forcing object from a TOML file."""
        ...

    @classmethod
    @abstractmethod
    def load_dict(cls, attrs: dict[str, Any] | IForcing) -> IForcing:
        """Create a forcing object from a dictionary of attributes."""
        ...

    @classmethod
    @abstractmethod
    def read_forcing(
        cls,
        filepath: Path,
    ) -> tuple[Type[IForcing], ForcingType, ForcingSource]:
        """Extract forcing class, type and source from a TOML file."""
        ...

    @classmethod
    @abstractmethod
    def get_forcing_class(
        cls, type: ForcingType, source: ForcingSource
    ) -> Type[IForcing]:
        """Get the forcing class corresponding to the type and source."""
        ...

    @classmethod
    @abstractmethod
    def list_forcing_types(cls) -> List[ForcingType]:
        """List all available forcing types."""
        ...

    @classmethod
    @abstractmethod
    def list_forcing_classes(cls) -> List[Type[IForcing]]:
        """List all available forcing classes."""
        ...

    @classmethod
    @abstractmethod
    def list_forcing_types_and_sources(cls) -> List[tuple[ForcingType, ForcingSource]]:
        """List all available combinations of forcing types and sources."""
        ...
