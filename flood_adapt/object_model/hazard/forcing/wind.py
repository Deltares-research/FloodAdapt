import os
import shutil
from pathlib import Path
from typing import Optional

import pandas as pd
import xarray as xr
from pydantic import Field

from flood_adapt.object_model.hazard.forcing.netcdf import validate_netcdf_forcing
from flood_adapt.object_model.hazard.forcing.timeseries import SyntheticTimeseries
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    IWind,
)
from flood_adapt.object_model.hazard.interface.timeseries import (
    SyntheticTimeseriesModel,
    TimeModel,
)
from flood_adapt.object_model.io import unit_system as us
from flood_adapt.object_model.io.csv import read_csv


class WindConstant(IWind):
    source: ForcingSource = ForcingSource.CONSTANT

    speed: us.UnitfulVelocity
    direction: us.UnitfulDirection

    def to_dataframe(self, time_frame: TimeModel) -> pd.DataFrame:
        time = pd.date_range(
            start=time_frame.start_time,
            end=time_frame.end_time,
            freq=TimeModel().time_step,
            name="time",
        )
        data = {
            "mag": [self.speed.value for _ in range(len(time))],
            "dir": [self.direction.value for _ in range(len(time))],
        }
        return pd.DataFrame(data=data, index=time)


class WindSynthetic(IWind):
    source: ForcingSource = ForcingSource.SYNTHETIC

    magnitude: SyntheticTimeseriesModel[us.UnitfulVelocity]
    direction: SyntheticTimeseriesModel[us.UnitfulDirection]

    def to_dataframe(self, time_frame: TimeModel) -> pd.DataFrame:
        time = pd.date_range(
            start=time_frame.start_time,
            end=time_frame.end_time,
            freq=TimeModel().time_step,
            name="time",
        )
        magnitude = SyntheticTimeseries(self.magnitude).to_dataframe(
            time_frame=time_frame,
        )
        direction = SyntheticTimeseries(self.direction).to_dataframe(
            time_frame=time_frame,
        )
        return pd.DataFrame(
            index=time,
            data={
                "mag": magnitude.reindex(time).to_numpy().flatten(),
                "dir": direction.reindex(time).to_numpy().flatten(),
            },
        )


class WindTrack(IWind):
    source: ForcingSource = ForcingSource.TRACK

    path: Optional[Path] = Field(default=None)
    # path to spw file, set this when creating it

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        if self.path:
            output_dir = Path(output_dir).resolve()
            if self.path == output_dir / self.path.name:
                return
            output_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.path, output_dir)
            self.path = output_dir / self.path.name


class WindCSV(IWind):
    source: ForcingSource = ForcingSource.CSV

    path: Path

    def to_dataframe(self, time_frame: TimeModel) -> pd.DataFrame:
        # TODO: slice data to time_frame like in WaterlevelCSV
        return read_csv(self.path)

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        if self.path:
            output_dir = Path(output_dir).resolve()
            if self.path == output_dir / self.path.name:
                return
            output_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.path, output_dir)
            self.path = output_dir / self.path.name


class WindMeteo(IWind):
    source: ForcingSource = ForcingSource.METEO


class WindNetCDF(IWind):
    source: ForcingSource = ForcingSource.NETCDF
    unit: us.UnitTypesVelocity = us.UnitTypesVelocity.mps

    path: Path

    def read(self) -> xr.Dataset:
        required_vars = ("wind10_v", "wind10_u", "press_msl")
        required_coords = ("time", "lat", "lon")
        with xr.open_dataset(self.path) as ds:
            validated_ds = validate_netcdf_forcing(ds, required_vars, required_coords)
        return validated_ds

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        if self.path:
            output_dir = Path(output_dir).resolve()
            if self.path == output_dir / self.path.name:
                return
            output_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.path, output_dir)
            self.path = output_dir / self.path.name
