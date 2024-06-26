import os
from abc import abstractmethod
from enum import Enum

import pandas as pd
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
    FILE = "FILE"
    SYNTHETIC = "SYNTHETIC"


class IForcing(BaseModel):
    """BaseModel describing the expected variables and data types for forcing parameters of hazard model."""

    _type: ForcingType = None
    _source: ForcingSource = None

    def to_csv(self, path: str | os.PathLike):
        self.get_data().to_csv(path)

    @abstractmethod
    def get_data(self) -> pd.DataFrame:
        """Return the forcing data as a pandas DataFrame."""
        pass
