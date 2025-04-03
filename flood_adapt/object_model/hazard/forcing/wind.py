import os
from pathlib import Path
from typing import Any

import pandas as pd
import xarray as xr
from pydantic import model_validator

from flood_adapt.object_model.hazard.forcing.netcdf import validate_netcdf_forcing
from flood_adapt.object_model.hazard.forcing.timeseries import (
    CSVTimeseries,
    SyntheticTimeseries,
    SyntheticTimeseriesModel,
    TimeModel,
)
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    IWind,
)
from flood_adapt.object_model.io import unit_system as us
from flood_adapt.object_model.utils import copy_file_to_output_dir


class WindConstant(IWind):
    source: ForcingSource = ForcingSource.CONSTANT

    speed: us.UnitfulVelocity
    direction: us.UnitfulDirection

    def to_dataframe(self, time_frame: TimeModel) -> pd.DataFrame:
        time = pd.date_range(
            start=time_frame.start_time,
            end=time_frame.end_time,
            freq=time_frame.time_step,
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
            freq=time_frame.time_step,
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

    path: Path
    # path to cyc file, set this when creating it

    @model_validator(mode="after")
    def validate_path(self):
        if self.path.suffix not in [".cyc", ".spw"]:
            raise ValueError(
                f"Invalid file extension: {self.path}. Allowed extensions are `.cyc` and `.spw`."
            )
        return self

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        if self.path:
            self.path = copy_file_to_output_dir(self.path, Path(output_dir))


class WindCSV(IWind):
    source: ForcingSource = ForcingSource.CSV

    path: Path

    units: dict[str, Any] = {
        "speed": us.UnitTypesVelocity.mps,
        "direction": us.UnitTypesDirection.degrees,
    }

    def to_dataframe(self, time_frame: TimeModel) -> pd.DataFrame:
        return CSVTimeseries[self.units].load_file(self.path).to_dataframe(time_frame)

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        self.path = copy_file_to_output_dir(self.path, Path(output_dir))


class WindMeteo(IWind):
    source: ForcingSource = ForcingSource.METEO


class WindNetCDF(IWind):
    source: ForcingSource = ForcingSource.NETCDF
    units: us.UnitTypesVelocity = us.UnitTypesVelocity.mps

    path: Path

    def read(self) -> xr.Dataset:
        required_vars = ("wind10_v", "wind10_u", "press_msl")
        required_coords = ("time", "lat", "lon")
        with xr.open_dataset(self.path) as ds:
            validated_ds = validate_netcdf_forcing(ds, required_vars, required_coords)
        return validated_ds

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        self.path = copy_file_to_output_dir(self.path, Path(output_dir))
