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

    def to_dataframe(self, time_frame: TimeModel) -> pd.DataFrame:
        time = pd.date_range(
            start=time_frame.start_time,
            end=time_frame.end_time,
            freq=TimeModel().time_step,
            name="time",
        )
        magnitude = (
            SyntheticTimeseries()
            .load_dict(self.magnitude)
            .to_dataframe(
                time_frame=time_frame,
            )
        )
        direction = (
            SyntheticTimeseries()
            .load_dict(self.direction)
            .to_dataframe(
                time_frame=time_frame,
            )
        )
        return pd.DataFrame(
            index=time,
            data={
                "mag": magnitude.reindex(time).to_numpy().flatten(),
                "dir": direction.reindex(time).to_numpy().flatten(),
            },
        )

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

    def to_dataframe(self, time_frame: TimeModel) -> pd.DataFrame:
        # TODO: slice data to time_frame like in WaterlevelCSV
        return read_csv(self.path)

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

    @classmethod
    def default(cls) -> "WindMeteo":
        return WindMeteo()


class WindNetCDF(IWind):
    source: ForcingSource = ForcingSource.NETCDF
    unit: us.UnitTypesVelocity = us.UnitTypesVelocity.mps

    path: Path

    def read(self) -> xr.Dataset:
        ds = xr.open_dataset(self.path)
        required_vars = {"wind10_v", "wind10_u", "press_msl"}
        required_coords = {"time", "lat", "lon"}
        return validate_netcdf_forcing(ds, required_vars, required_coords)

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        if self.path:
            output_dir = Path(output_dir)
            if self.path == output_dir / self.path.name:
                return
            output_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.path, output_dir)
            self.path = output_dir / self.path.name

    @classmethod
    def default(cls) -> "WindNetCDF":
        return WindNetCDF(Path("path/to/forcing.nc"))
