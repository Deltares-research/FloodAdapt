import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar, Optional

import pandas as pd
import xarray as xr
from pydantic import Field

import flood_adapt.object_model.io.unitfulvalue as uv
from flood_adapt.object_model.hazard.event.meteo import MeteoHandler
from flood_adapt.object_model.hazard.event.timeseries import (
    DEFAULT_TIMESTEP,
    CSVTimeseries,
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


class RainfallConstant(IRainfall):
    _source: ClassVar[ForcingSource] = ForcingSource.CONSTANT

    intensity: uv.UnitfulIntensity

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
        return cls(
            intensity=uv.UnitfulIntensity(value=0, units=uv.UnitTypesIntensity.mm_hr)
        )


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
                self.logger.error(f"Error loading synthetic rainfall timeseries: {e}")

    @staticmethod
    def default() -> "RainfallSynthetic":
        return RainfallSynthetic(
            timeseries=SyntheticTimeseriesModel.default(uv.UnitfulIntensity)
        )


class RainfallMeteo(IRainfall):
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
                self.logger.error(f"Error reading meteo data: {self.path}. {e}")

    @staticmethod
    def default() -> "RainfallMeteo":
        return RainfallMeteo()


class RainfallTrack(IRainfall):
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
        pass

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        if self.path:
            output_dir = Path(output_dir)
            if self.path == output_dir / self.path.name:
                return
            output_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.path, output_dir)
            self.path = output_dir / self.path.name

    @staticmethod
    def default() -> "RainfallTrack":
        return RainfallTrack()


class RainfallCSV(IRainfall):
    _source: ClassVar[ForcingSource] = ForcingSource.CSV

    path: Path

    def get_data(self, t0=None, t1=None, strict=True, **kwargs) -> pd.DataFrame:
        t0, t1 = self.parse_time(t0, t1)
        try:
            return CSVTimeseries.load_file(path=self.path).to_dataframe(
                start_time=t0, end_time=t1
            )
        except Exception as e:
            if strict:
                raise
            else:
                self.logger.error(f"Error reading CSV file: {self.path}. {e}")

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        if self.path:
            output_dir = Path(output_dir)
            if self.path == output_dir / self.path.name:
                return
            output_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.path, output_dir)
            self.path = output_dir / self.path.name

    @staticmethod
    def default() -> "RainfallCSV":
        return RainfallCSV(path="path/to/rainfall.csv")