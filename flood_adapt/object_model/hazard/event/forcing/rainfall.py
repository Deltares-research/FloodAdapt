import os
from datetime import datetime
from typing import ClassVar

import pandas as pd
import xarray as xr
from pydantic import Field

from flood_adapt.object_model.hazard.event.meteo import read_meteo
from flood_adapt.object_model.hazard.event.timeseries import (
    DEFAULT_TIMESTEP,
    SyntheticTimeseries,
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.hazard.interface.forcing import (
    IRainfall,
)
from flood_adapt.object_model.hazard.interface.models import (
    REFERENCE_TIME,
    ForcingSource,
)
from flood_adapt.object_model.io.unitfulvalue import UnitfulIntensity, UnitfulTime


class RainfallConstant(IRainfall):
    _source: ClassVar[ForcingSource] = ForcingSource.CONSTANT

    intensity: UnitfulIntensity

    def get_data(
        self, strict=True, t0: datetime = None, t1: datetime = None
    ) -> pd.DataFrame:
        if t0 is None:
            t0 = REFERENCE_TIME
        elif isinstance(t0, UnitfulTime):
            t0 = REFERENCE_TIME + t0.to_timedelta()

        if t1 is None:
            t1 = t0 + UnitfulTime(value=1, units="hr").to_timedelta()
        elif isinstance(t1, UnitfulTime):
            t1 = t0 + t1.to_timedelta()

        time = pd.date_range(start=t0, end=t1, freq=DEFAULT_TIMESTEP.to_timedelta())
        values = [self.intensity.value for _ in range(len(time))]
        return pd.DataFrame(data=values, index=time)

    @classmethod
    def default(cls) -> "RainfallConstant":
        return RainfallConstant(intensity=UnitfulIntensity(value=0, units="mm/hr"))


class RainfallSynthetic(IRainfall):
    _source: ClassVar[ForcingSource] = ForcingSource.SYNTHETIC
    timeseries: SyntheticTimeseriesModel

    def get_data(
        self, strict=True, t0: datetime = None, t1: datetime = None
    ) -> pd.DataFrame:
        rainfall = SyntheticTimeseries().load_dict(data=self.timeseries)

        if t0 is None:
            t0 = REFERENCE_TIME
        elif isinstance(t0, UnitfulTime):
            t0 = REFERENCE_TIME + t0.to_timedelta()

        if t1 is None:
            t1 = t0 + rainfall.attrs.duration.to_timedelta()
        elif isinstance(t1, UnitfulTime):
            t1 = t0 + t1.to_timedelta()

        try:
            return rainfall.to_dataframe(start_time=t0, end_time=t1)
        except Exception as e:
            if strict:
                raise
            else:
                self._logger.error(f"Error loading synthetic rainfall timeseries: {e}")

    @classmethod
    def default(cls) -> "RainfallSynthetic":
        return RainfallSynthetic(
            timeseries=SyntheticTimeseriesModel.default(UnitfulIntensity)
        )


class RainfallFromMeteo(IRainfall):
    _source: ClassVar[ForcingSource] = ForcingSource.METEO
    path: str | os.PathLike | None = Field(default=None)
    # path to the meteo data, set this when downloading it

    def get_data(self, strict=True) -> xr.DataArray:
        try:
            if self.path is None:
                raise ValueError(
                    "Meteo path is not set. Download the meteo dataset first using HistoricalEvent.download_meteo().."
                )

            return read_meteo(meteo_dir=self.path)[
                "precip"
            ]  # use `.to_dataframe()` to convert to pd.DataFrame
        except Exception as e:
            if strict:
                raise
            else:
                self._logger.error(f"Error reading meteo data: {self.path}. {e}")

    @classmethod
    def default(cls) -> "RainfallFromMeteo":
        return RainfallFromMeteo()


class RainfallFromTrack(IRainfall):
    _source: ClassVar[ForcingSource] = ForcingSource.TRACK

    path: str | os.PathLike | None = Field(default=None)
    # path to spw file, set this when creating it

    def get_data(self, strict=True) -> pd.DataFrame:
        return self.path  # TODO implement

    @classmethod
    def default(cls) -> "RainfallFromTrack":
        return RainfallFromTrack()
