import os
from pathlib import Path
from typing import Annotated, Any

import pandas as pd
import xarray as xr

from flood_adapt.misc.utils import (
    copy_file_to_output_dir,
    validate_file_extension,
)
from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.forcing.forcing import (
    ForcingSource,
    IWind,
)
from flood_adapt.objects.forcing.netcdf import validate_netcdf_forcing
from flood_adapt.objects.forcing.timeseries import (
    CSVTimeseries,
    SyntheticTimeseries,
    TimeFrame,
    TimeseriesFactory,
)


class WindConstant(IWind):
    source: ForcingSource = ForcingSource.CONSTANT

    speed: us.UnitfulVelocity
    direction: us.UnitfulDirection

    def to_dataframe(self, time_frame: TimeFrame) -> pd.DataFrame:
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

    magnitude: SyntheticTimeseries
    direction: SyntheticTimeseries

    def to_dataframe(self, time_frame: TimeFrame) -> pd.DataFrame:
        time = pd.date_range(
            start=time_frame.start_time,
            end=time_frame.end_time,
            freq=time_frame.time_step,
            name="time",
        )

        magnitude = TimeseriesFactory.from_object(self.magnitude).to_dataframe(
            time_frame=time_frame,
        )

        direction = TimeseriesFactory.from_object(self.direction).to_dataframe(
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

    path: Annotated[Path, validate_file_extension([".cyc", ".spw"])]
    # path to cyc file, set this when creating it

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        if self.path:
            self.path = copy_file_to_output_dir(self.path, Path(output_dir))


class WindCSV(IWind):
    source: ForcingSource = ForcingSource.CSV

    path: Annotated[Path, validate_file_extension([".csv"])]

    units: dict[str, Any] = {
        "speed": us.UnitTypesVelocity.mps,
        "direction": us.UnitTypesDirection.degrees,
    }

    def to_dataframe(self, time_frame: TimeFrame) -> pd.DataFrame:
        return CSVTimeseries.load_file(
            path=self.path, units=us.UnitfulVelocity(value=0, units=self.units["speed"])
        ).to_dataframe(time_frame)

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        self.path = copy_file_to_output_dir(self.path, Path(output_dir))


class WindMeteo(IWind):
    source: ForcingSource = ForcingSource.METEO


class WindNetCDF(IWind):
    source: ForcingSource = ForcingSource.NETCDF
    units: us.UnitTypesVelocity = us.UnitTypesVelocity.mps

    path: Annotated[Path, validate_file_extension([".nc"])]

    def read(self) -> xr.Dataset:
        required_vars = ("wind10_v", "wind10_u", "press_msl")
        required_coords = ("time", "lat", "lon")
        with xr.open_dataset(self.path) as ds:
            validated_ds = validate_netcdf_forcing(ds, required_vars, required_coords)
        return validated_ds

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        self.path = copy_file_to_output_dir(self.path, Path(output_dir))
