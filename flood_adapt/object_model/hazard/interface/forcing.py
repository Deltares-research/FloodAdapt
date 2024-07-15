import os
from abc import abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any

import pandas as pd
import tomli
from pydantic import BaseModel


class ForcingType(str, Enum):
    """Enum class for the different types of forcing parameters."""

    WIND = "WIND"
    RAINFALL = "RAINFALL"
    DISCHARGE = "DISCHARGE"
    WATERLEVEL = "WATERLEVEL"


class ForcingSource(str, Enum):
    """Enum class for the different sources of forcing parameters."""

    MODEL = "MODEL"
    TRACK = "TRACK"
    CSV = "CSV"
    SYNTHETIC = "SYNTHETIC"
    GAUGED = "GAUGED"
    CONSTANT = "CONSTANT"
    METEO = "METEO"
    SPW_FILE = "SPW_FILE"


class IForcing(BaseModel):
    """BaseModel describing the expected variables and data types for forcing parameters of hazard model."""

    _type: ForcingType = None
    _source: ForcingSource = None

    def to_csv(self, path: str | os.PathLike):
        self.get_data().to_csv(path)

    @classmethod
    def load_file(cls, path: str | os.PathLike):
        with open(path, mode="rb") as fp:
            toml_data = tomli.load(fp)
        return cls.load_dict(toml_data)

    @classmethod
    def load_dict(cls, attrs):
        return cls.model_validate(attrs)

    @abstractmethod
    def get_data(self) -> pd.DataFrame:
        """Return the forcing data as a pandas DataFrame."""
        pass


class IDischarge(IForcing):
    _type = ForcingType.DISCHARGE


class IRainfall(IForcing):
    _type = ForcingType.RAINFALL


class IWind(IForcing):
    _type = ForcingType.WIND


class IWaterlevel(IForcing):
    _type = ForcingType.WATERLEVEL


class IForcingFactory:
    @classmethod
    @abstractmethod
    def load_file(cls, toml_file: Path) -> IForcing:
        pass

    @classmethod
    @abstractmethod
    def load_dict(cls, attrs: dict[str, Any]) -> IForcing:
        pass
