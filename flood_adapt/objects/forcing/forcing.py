import hashlib
import json
import os
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any, Type, TypeVar

from pydantic import BaseModel, field_serializer

from flood_adapt.config.hazard import RiverModel
from flood_adapt.misc.io import read_toml


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


T = TypeVar("T", bound="IForcing")


class IForcing(BaseModel, ABC):
    """BaseModel describing the expected variables and data types for forcing parameters of hazard model."""

    class Config:
        arbitrary_types_allowed = True

    type: ForcingType
    source: ForcingSource

    @classmethod
    def load_file(cls: Type[T], path: Path, **kwargs) -> T:
        data = read_toml(path)
        instance = cls.model_validate(data)
        instance._post_load(file_path=path, **kwargs)
        return instance

    @classmethod
    def load_dict(cls: Type[T], attrs: dict) -> T:
        return cls.model_validate(attrs)

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Override the default model_dump to include class variables `type` and `source`."""
        data = super().model_dump(**kwargs)
        data.update({"type": self.type, "source": self.source})
        return data

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        """Save additional data of the forcing."""
        pass

    @field_serializer("path", check_fields=False)
    @classmethod
    def serialize_path(cls, value: Path) -> str:
        """Serialize filepath-like fields by saving only the filename. It is assumed that the file will be saved in the same directory."""
        return value.name

    def content_fingerprint(self) -> str:
        """Return a stable fingerprint of the forcing's underlying data.

        - If a file-backed `path` attribute exists and the file exists, hash its bytes (SHA-256).
        - Otherwise, hash a canonical JSON dump of the model (excluding volatile fields like `path`).

        Returns
        -------
        str
            A fingerprint string that changes when the forcing's effective data changes.
        """
        # Prefer hashing the actual file content when available
        try:
            p = getattr(self, "path", None)
            if isinstance(p, Path) and p and p.exists():
                sha = hashlib.sha256()
                with p.open("rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        sha.update(chunk)
                # Include filename to disambiguate multi-forcing scenarios with identical content
                return f"FILE:{p.name}:{sha.hexdigest()}"
        except Exception:
            # Fall through to attribute-based hashing if anything goes wrong
            pass

        # Fallback: hash the model attributes (excluding volatile fields like path)
        data = self.model_dump(exclude_none=True)
        # Remove potentially non-stable/absolute fields
        data.pop("path", None)

        # Ensure enums are serialized to their values for stable hashing
        if isinstance(data.get("type"), Enum):
            data["type"] = data["type"].value
        if isinstance(data.get("source"), Enum):
            data["source"] = data["source"].value

        payload = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
        return f"ATTR:{hashlib.sha256(payload).hexdigest()}"

    def _post_load(self, file_path: Path | str | os.PathLike, **kwargs) -> None:
        """Post-load hook, called at the end of `load_file`, to perform any additional loading steps after loading from file."""
        return


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
    def load_file(cls, toml_file: Path, **kwargs) -> IForcing:
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
    ) -> tuple[type[IForcing], ForcingType, ForcingSource]:
        """Extract forcing class, type and source from a TOML file."""
        ...

    @classmethod
    @abstractmethod
    def get_forcing_class(
        cls, type: ForcingType, source: ForcingSource
    ) -> type[IForcing]:
        """Get the forcing class corresponding to the type and source."""
        ...

    @classmethod
    @abstractmethod
    def list_forcing_types(cls) -> list[ForcingType]:
        """List all available forcing types."""
        ...

    @classmethod
    @abstractmethod
    def list_forcing_classes(cls) -> list[type[IForcing]]:
        """List all available forcing classes."""
        ...

    @classmethod
    @abstractmethod
    def list_forcing_types_and_sources(cls) -> list[tuple[ForcingType, ForcingSource]]:
        """List all available combinations of forcing types and sources."""
        ...
