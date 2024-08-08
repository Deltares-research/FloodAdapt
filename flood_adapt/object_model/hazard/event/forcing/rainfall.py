import os
from typing import ClassVar

import pandas as pd
import xarray as xr
from pydantic import Field

from flood_adapt.object_model.hazard.event.meteo import read_meteo
from flood_adapt.object_model.hazard.event.timeseries import (
    SyntheticTimeseries,
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.hazard.interface.forcing import (
    IRainfall,
)
from flood_adapt.object_model.hazard.interface.models import (
    ForcingSource,
)
from flood_adapt.object_model.io.unitfulvalue import UnitfulIntensity


class RainfallConstant(IRainfall):
    _source: ClassVar[ForcingSource] = ForcingSource.CONSTANT

    intensity: UnitfulIntensity

    @classmethod
    def default(cls) -> "RainfallConstant":
        return RainfallConstant(intensity=UnitfulIntensity(value=0, units="mm/h"))


class RainfallSynthetic(IRainfall):
    _source: ClassVar[ForcingSource] = ForcingSource.SYNTHETIC
    timeseries: SyntheticTimeseriesModel

    def get_data(self) -> pd.DataFrame:
        return pd.DataFrame(
            SyntheticTimeseries().load_dict(self.timeseries).calculate_data()
        )

    @classmethod
    def default(cls) -> "RainfallSynthetic":
        return RainfallSynthetic(timeseries=SyntheticTimeseriesModel().default())


class RainfallFromMeteo(IRainfall):
    _source: ClassVar[ForcingSource] = ForcingSource.METEO
    path: str | os.PathLike | None = Field(default=None)
    # path to the meteo data, set this when downloading it

    def get_data(self) -> xr.DataArray:
        if self.path is None:
            raise ValueError(
                "Meteo path is not set. Download the meteo dataset first using HistoricalEvent.download_meteo().."
            )

        return read_meteo(meteo_dir=self.path)[
            "precip"
        ]  # use `.to_dataframe()` to convert to pd.DataFrame

    @classmethod
    def default(cls) -> "RainfallFromMeteo":
        return RainfallFromMeteo()


class RainfallFromTrack(IRainfall):
    _source: ClassVar[ForcingSource] = ForcingSource.TRACK

    path: str | os.PathLike | None = Field(default=None)
    # path to spw file, set this when creating it

    def get_data(self) -> pd.DataFrame:
        return self.path  # TODO implement

    @classmethod
    def default(cls) -> "RainfallFromTrack":
        return RainfallFromTrack()
