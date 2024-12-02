import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import xarray as xr
from pydantic import Field

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
from flood_adapt.object_model.io import unit_system as us
from flood_adapt.object_model.io.csv import read_csv


class WindConstant(IWind):
    source: ForcingSource = ForcingSource.CONSTANT

    speed: us.UnitfulVelocity
    direction: us.UnitfulDirection

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

    @classmethod
    def default(cls) -> "WindConstant":
        return WindConstant(
            speed=us.UnitfulVelocity(value=10, units=us.UnitTypesVelocity.mps),
            direction=us.UnitfulDirection(value=0, units=us.UnitTypesDirection.degrees),
        )


class WindSynthetic(IWind):
    source: ForcingSource = ForcingSource.SYNTHETIC

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

    @classmethod
    def default(cls) -> "WindSynthetic":
        return WindSynthetic(
            magnitude=SyntheticTimeseriesModel.default(us.UnitfulVelocity),
            direction=SyntheticTimeseriesModel.default(us.UnitfulDirection),
        )


class WindTrack(IWind):
    source: ForcingSource = ForcingSource.TRACK

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

    @classmethod
    def default(cls) -> "WindTrack":
        return WindTrack()


class WindCSV(IWind):
    source: ForcingSource = ForcingSource.CSV

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

    @classmethod
    def default(cls) -> "WindCSV":
        return WindCSV(path="path/to/wind.csv")


class WindMeteo(IWind):
    source: ForcingSource = ForcingSource.METEO

    # Required variables: ['wind10_u' (m/s), 'wind10_v' (m/s)]
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

    @classmethod
    def default(cls) -> "WindMeteo":
        return WindMeteo()
