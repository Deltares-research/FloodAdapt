import os
import shutil
from datetime import datetime
from typing import ClassVar

import pandas as pd
import xarray as xr
from pydantic import Field

from flood_adapt.object_model.hazard.event.timeseries import SyntheticTimeseries
from flood_adapt.object_model.hazard.interface.forcing import IWind
from flood_adapt.object_model.hazard.interface.models import (
    DEFAULT_TIMESTEP,
    REFERENCE_TIME,
    ForcingSource,
)
from flood_adapt.object_model.hazard.interface.timeseries import (
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.io.csv import read_csv
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDirection,
    UnitfulTime,
    UnitfulVelocity,
    UnitTypesDirection,
    UnitTypesTime,
    UnitTypesVelocity,
)


class WindConstant(IWind):
    _source: ClassVar[ForcingSource] = ForcingSource.CONSTANT

    speed: UnitfulVelocity
    direction: UnitfulDirection

    def get_data(
        self, strict=True, t0: datetime = None, t1: datetime = None
    ) -> pd.DataFrame:
        if t0 is None:
            t0 = REFERENCE_TIME
        elif isinstance(t0, UnitfulTime):
            t0 = REFERENCE_TIME + t0.to_timedelta()

        if t1 is None:
            t1 = t0 + UnitfulTime(value=1, units=UnitTypesTime.hours).to_timedelta()
        elif isinstance(t1, UnitfulTime):
            t1 = t0 + t1.to_timedelta()

        time = pd.date_range(start=t0, end=t1, freq=DEFAULT_TIMESTEP.to_timedelta())
        values = [
            [self.speed.value for _ in range(len(time))],
            [self.direction.value for _ in range(len(time))],
        ]

        return pd.DataFrame(data=values, index=time)

    @classmethod
    def default(cls) -> "WindConstant":
        return WindConstant(
            speed=UnitfulVelocity(value=10, units=UnitTypesVelocity.mps),
            direction=UnitfulDirection(value=0, units=UnitTypesDirection.degrees),
        )


class WindSynthetic(IWind):
    _source: ClassVar[ForcingSource] = ForcingSource.SYNTHETIC

    timeseries: SyntheticTimeseriesModel

    def get_data(
        self, strict=True, t0: datetime = None, t1: datetime = None
    ) -> pd.DataFrame:
        try:
            return pd.DataFrame(
                SyntheticTimeseries().load_dict(self.timeseries).calculate_data()
            )
        except Exception as e:
            if strict:
                raise
            else:
                self._logger.error(f"Error loading synthetic wind timeseries: {e}")

    @classmethod
    def default(cls) -> "WindSynthetic":
        return WindSynthetic(
            timeseries=SyntheticTimeseriesModel.default(UnitfulVelocity)
        )


class WindFromTrack(IWind):
    _source: ClassVar[ForcingSource] = ForcingSource.TRACK

    path: str | os.PathLike | None = Field(default=None)
    # path to spw file, set this when creating it

    def get_data(
        self, strict=True, t0: datetime = None, t1: datetime = None
    ) -> pd.DataFrame:
        return self.path

    def save_additional(self, path: str | os.PathLike):
        if self.path:
            shutil.copy2(self.path, path)

    @classmethod
    def default(cls) -> "WindFromTrack":
        return WindFromTrack()


class WindFromCSV(IWind):
    _source: ClassVar[ForcingSource] = ForcingSource.CSV

    path: str | os.PathLike

    def get_data(
        self, strict=True, t0: datetime = None, t1: datetime = None
    ) -> pd.DataFrame:
        try:
            return read_csv(self.path)
        except Exception as e:
            if strict:
                raise
            else:
                self._logger.error(f"Error reading CSV file: {self.path}. {e}")

    def save_additional(self, path: str | os.PathLike):
        if self.path:
            shutil.copy2(self.path, path)

    @classmethod
    def default(cls) -> "WindFromCSV":
        return WindFromCSV(path="path/to/wind.csv")


class WindFromMeteo(IWind):
    _source: ClassVar[ForcingSource] = ForcingSource.METEO

    path: str | os.PathLike | None = Field(default=None)
    # simpath of the offshore model, set this when running the offshore model

    # Required variables: ['wind_u' (m/s), 'wind_v' (m/s)]
    # Required coordinates: ['time', 'mag', 'dir']

    def get_data(self, strict=True, **kwargs) -> xr.DataArray:
        try:
            if self.path is None:
                raise ValueError(
                    "Meteo path is not set. Download the meteo dataset first using HistoricalEvent.download_meteo().."
                )

            from flood_adapt.object_model.hazard.event.meteo import read_meteo

            # ASSUMPTION: the download has been done already, see meteo.download_meteo().
            # TODO add to read_meteo to run download if not already downloaded.
            return read_meteo(meteo_dir=self.path)[["wind_u", "wind_v"]]
        except Exception as e:
            if strict:
                raise
            else:
                self._logger.error(f"Error reading meteo data: {self.path}. {e}")

    @classmethod
    def default(cls) -> "WindFromMeteo":
        return WindFromMeteo()
