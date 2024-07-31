import os
from abc import abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd
import tomli
from pydantic import BaseModel

from flood_adapt.object_model.hazard.interface.models import (
    ForcingSource,
    ForcingType,
    TimeModel,
)
from flood_adapt.object_model.interface.site import SiteModel


class IForcing(BaseModel):
    """BaseModel describing the expected variables and data types for forcing parameters of hazard model."""

    _type: ForcingType = None
    _source: ForcingSource = None

    @classmethod
    def load_file(cls, path: str | os.PathLike):
        with open(path, mode="rb") as fp:
            toml_data = tomli.load(fp)
        return cls.load_dict(toml_data)

    @classmethod
    def load_dict(cls, attrs):
        return cls.model_validate(attrs)

    def process(self, time: TimeModel, site: SiteModel):
        """Generate the forcing data and store the result in the forcing.

        The default implementation is to do nothing. If the forcing data needs to be created/downloaded/computed as it is not directly stored in the forcing instance, this method should be overridden.
        """
        return

    def get_data(self) -> pd.DataFrame:
        """If applicable, return the forcing/timeseries data as a (pd.DataFrame | xr.DataSet | arrayLike) data structure.

        The default implementation is to return None, if it makes sense to return an arrayLike datastructure, return it, otherwise return None.
        """
        return


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
