import os
from typing import ClassVar

import pandas as pd
import xarray as xr
from pydantic import Field

from flood_adapt.object_model.hazard.event.timeseries import SyntheticTimeseries
from flood_adapt.object_model.hazard.interface.forcing import IWind
from flood_adapt.object_model.hazard.interface.models import ForcingSource
from flood_adapt.object_model.hazard.interface.timeseries import (
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.io.unitfulvalue import UnitfulDirection, UnitfulVelocity


class WindConstant(IWind):
    _source: ClassVar[ForcingSource] = ForcingSource.CONSTANT

    speed: UnitfulVelocity
    direction: UnitfulDirection

    @classmethod
    def default(cls) -> "WindConstant":
        return WindConstant(
            speed=UnitfulVelocity(10, "m/s"),
            direction=UnitfulDirection(0, "deg N"),
        )


class WindSynthetic(IWind):
    _source: ClassVar[ForcingSource] = ForcingSource.SYNTHETIC

    timeseries: SyntheticTimeseriesModel

    def get_data(self) -> pd.DataFrame:
        return pd.DataFrame(
            SyntheticTimeseries().load_dict(self.timeseries).calculate_data()
        )

    @classmethod
    def default(cls) -> "WindSynthetic":
        return WindSynthetic(timeseries=SyntheticTimeseriesModel().default())


class WindFromTrack(IWind):
    _source: ClassVar[ForcingSource] = ForcingSource.TRACK

    path: str | os.PathLike | None = Field(default=None)
    # path to spw file, set this when creating it

    def get_data(self) -> pd.DataFrame:
        return self.path

    @classmethod
    def default(cls) -> "WindFromTrack":
        return WindFromTrack()


class WindFromCSV(IWind):
    _source: ClassVar[ForcingSource] = ForcingSource.CSV

    path: str | os.PathLike

    def get_data(self) -> pd.DataFrame:
        df = pd.read_csv(
            self.path,
            index_col=0,
            header=None,
        )
        df.index = pd.DatetimeIndex(df.index)
        return df

    @classmethod
    def default(cls) -> "WindFromCSV":
        return WindFromCSV(path="path/to/wind.csv")


class WindFromMeteo(IWind):
    _source: ClassVar[ForcingSource] = ForcingSource.METEO

    path: str | os.PathLike | None = Field(default=None)
    # simpath of the offshore model, set this when running the offshore model

    # Required variables: ['wind_u' (m/s), 'wind_v' (m/s)]
    # Required coordinates: ['time', 'mag', 'dir']

    def get_data(self) -> xr.DataArray:
        if self.path is None:
            raise ValueError(
                "Meteo path is not set. Download the meteo dataset first using HistoricalEvent.download_meteo().."
            )

        from flood_adapt.object_model.hazard.event.meteo import read_meteo

        # ASSUMPTION: the download has been done already, see meteo.download_meteo().
        # TODO add to read_meteo to run download if not already downloaded.
        return read_meteo(meteo_dir=self.path)[["wind_u", "wind_v"]]

    @classmethod
    def default(cls) -> "WindFromMeteo":
        return WindFromMeteo()
