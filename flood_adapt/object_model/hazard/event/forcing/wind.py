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
from flood_adapt.object_model.hazard.event.timeseries import SyntheticTimeseries
from flood_adapt.object_model.hazard.interface.forcing import IWind
from flood_adapt.object_model.hazard.interface.models import (
    DEFAULT_TIMESTEP,
    ForcingSource,
    TimeModel,
)
from flood_adapt.object_model.hazard.interface.timeseries import (
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.io.csv import read_csv


class WindConstant(IWind):
    _source: ClassVar[ForcingSource] = ForcingSource.CONSTANT

    speed: uv.UnitfulVelocity
    direction: uv.UnitfulDirection

    def get_data(
        self,
        t0: Optional[datetime] = None,
        t1: Optional[datetime] = None,
        strict: bool = True,
        **kwargs: Any,
    ) -> Optional[pd.DataFrame]:
        t0, t1 = self.parse_time(t0, t1)
        time = pd.date_range(
            start=t0, end=t1, freq=DEFAULT_TIMESTEP.to_timedelta(), name="time"
        )
        data = {
            "data_0": [self.speed.value for _ in range(len(time))],
            "data_1": [self.direction.value for _ in range(len(time))],
        }

        return pd.DataFrame(data=data, index=time)

    @staticmethod
    def default() -> "WindConstant":
        return WindConstant(
            speed=uv.UnitfulVelocity(value=10, units=uv.UnitTypesVelocity.mps),
            direction=uv.UnitfulDirection(value=0, units=uv.UnitTypesDirection.degrees),
        )


class WindSynthetic(IWind):
    _source: ClassVar[ForcingSource] = ForcingSource.SYNTHETIC

    magnitude: SyntheticTimeseriesModel
    direction: SyntheticTimeseriesModel

    def get_data(
        self,
        t0: Optional[datetime] = None,
        t1: Optional[datetime] = None,
        strict: bool = True,
        **kwargs: Any,
    ) -> Optional[pd.DataFrame]:
        t0, t1 = self.parse_time(t0, t1)
        time = pd.date_range(
            start=t0, end=t1, freq=DEFAULT_TIMESTEP.to_timedelta(), name="time"
        )
        magnitude = SyntheticTimeseries().load_dict(self.magnitude).calculate_data()
        direction = SyntheticTimeseries().load_dict(self.direction).calculate_data()

        try:
            return pd.DataFrame(
                index=time,
                data={"mag": magnitude, "dir": direction},
            )
        except Exception as e:
            if strict:
                raise
            else:
                self.logger.error(f"Error loading synthetic wind timeseries: {e}")

    @staticmethod
    def default() -> "WindSynthetic":
        return WindSynthetic(
            magnitude=SyntheticTimeseriesModel.default(uv.UnitfulVelocity),
            direction=SyntheticTimeseriesModel.default(uv.UnitfulDirection),
        )


class WindTrack(IWind):
    _source: ClassVar[ForcingSource] = ForcingSource.TRACK

    path: Optional[Path] = Field(default=None)
    # path to spw file, set this when creating it

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        if self.path:
            output_dir = Path(output_dir)
            if self.path == output_dir / self.path.name:
                return
            output_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.path, output_dir)
            self.path = output_dir / self.path.name

    @staticmethod
    def default() -> "WindTrack":
        return WindTrack()


class WindCSV(IWind):
    _source: ClassVar[ForcingSource] = ForcingSource.CSV

    path: Path

    def get_data(
        self,
        t0: Optional[datetime] = None,
        t1: Optional[datetime] = None,
        strict: bool = True,
        **kwargs: Any,
    ) -> Optional[pd.DataFrame]:
        try:
            return read_csv(self.path)
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
    def default() -> "WindCSV":
        return WindCSV(path="path/to/wind.csv")


class WindMeteo(IWind):
    _source: ClassVar[ForcingSource] = ForcingSource.METEO

    # Required variables: ['wind_u' (m/s), 'wind_v' (m/s)]
    # Required coordinates: ['time', 'mag', 'dir']
    def get_data(
        self,
        t0: Optional[datetime] = None,
        t1: Optional[datetime] = None,
        strict: bool = True,
        **kwargs: Any,
    ) -> xr.Dataset:
        t0, t1 = self.parse_time(t0, t1)
        time = TimeModel(start_time=t0, end_time=t1)

        try:
            return MeteoHandler().read(time)
        except Exception as e:
            if strict:
                raise
            else:
                self.logger.error(f"Error reading meteo data: {e}")

    @staticmethod
    def default() -> "WindMeteo":
        return WindMeteo()