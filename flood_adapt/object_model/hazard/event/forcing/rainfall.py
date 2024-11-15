import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar, Optional

import pandas as pd
import xarray as xr
from pydantic import Field

from flood_adapt.object_model.hazard.event.meteo import MeteoHandler
from flood_adapt.object_model.hazard.event.timeseries import (
    DEFAULT_TIMESTEP,
    SyntheticTimeseries,
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.hazard.interface.forcing import (
    IRainfall,
)
from flood_adapt.object_model.hazard.interface.models import (
    ForcingSource,
    TimeModel,
)
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulIntensity,
    UnitTypesIntensity,
)


class RainfallConstant(IRainfall):
    _source: ClassVar[ForcingSource] = ForcingSource.CONSTANT

    intensity: UnitfulIntensity

    def get_data(
        self,
        t0: datetime = None,
        t1: datetime = None,
        strict=True,
    ) -> pd.DataFrame:
        t0, t1 = self.parse_time(t0, t1)
        time = pd.date_range(
            start=t0, end=t1, freq=DEFAULT_TIMESTEP.to_timedelta(), name="time"
        )
        values = [self.intensity.value for _ in range(len(time))]
        return pd.DataFrame(data=values, index=time)

    @classmethod
    def default(cls) -> "RainfallConstant":
        return cls(intensity=UnitfulIntensity(value=0, units=UnitTypesIntensity.mm_hr))


class RainfallSynthetic(IRainfall):
    _source: ClassVar[ForcingSource] = ForcingSource.SYNTHETIC
    timeseries: SyntheticTimeseriesModel

    def get_data(
        self,
        t0: Optional[datetime] = None,
        t1: Optional[datetime] = None,
        strict: bool = True,
        **kwargs: Any,
    ) -> Optional[pd.DataFrame]:
        rainfall = SyntheticTimeseries().load_dict(data=self.timeseries)
        if t1 is not None:
            t0, t1 = self.parse_time(t0, t1)
        else:
            t0, t1 = self.parse_time(t0, rainfall.attrs.duration)

        try:
            return rainfall.to_dataframe(start_time=t0, end_time=t1)
        except Exception as e:
            if strict:
                raise
            else:
                self._logger.error(f"Error loading synthetic rainfall timeseries: {e}")

    @staticmethod
    def default() -> "RainfallSynthetic":
        return RainfallSynthetic(
            timeseries=SyntheticTimeseriesModel.default(UnitfulIntensity)
        )


class RainfallFromMeteo(IRainfall):
    _source: ClassVar[ForcingSource] = ForcingSource.METEO

    def get_data(
        self,
        t0: Optional[datetime] = None,
        t1: Optional[datetime] = None,
        strict: bool = True,
        **kwargs: Any,
    ) -> xr.Dataset:
        t0, t1 = self.parse_time(t0, t1)
        time_frame = TimeModel(start_time=t0, end_time=t1)
        try:
            return MeteoHandler().read(time_frame)
        except Exception as e:
            if strict:
                raise
            else:
                self._logger.error(f"Error reading meteo data: {self.path}. {e}")

    @staticmethod
    def default() -> "RainfallFromMeteo":
        return RainfallFromMeteo()


class RainfallFromTrack(IRainfall):
    _source: ClassVar[ForcingSource] = ForcingSource.TRACK

    path: Optional[Path] = Field(default=None)
    # path to spw file, set this when creating it

    def get_data(
        self,
        t0: Optional[datetime] = None,
        t1: Optional[datetime] = None,
        strict: bool = True,
        **kwargs: Any,
    ) -> Optional[pd.DataFrame]:
        t0, t1 = self.parse_time(t0, t1)

        return self.path

    def save_additional(self, toml_dir: Path):
        if self.path:
            shutil.copy2(self.path, toml_dir)
            self.path = toml_dir / self.path.name

    @staticmethod
    def default() -> "RainfallFromTrack":
        return RainfallFromTrack()
