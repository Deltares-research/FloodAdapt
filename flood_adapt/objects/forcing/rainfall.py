import os
from pathlib import Path
from typing import Annotated

import pandas as pd
import xarray as xr

from flood_adapt.misc.utils import (
    copy_file_to_output_dir,
    validate_file_extension,
)
from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.forcing.forcing import (
    ForcingSource,
    IRainfall,
)
from flood_adapt.objects.forcing.netcdf import validate_netcdf_forcing
from flood_adapt.objects.forcing.time_frame import TimeFrame
from flood_adapt.objects.forcing.timeseries import (
    CSVTimeseries,
    SyntheticTimeseries,
    TimeseriesFactory,
)


class RainfallConstant(IRainfall):
    source: ForcingSource = ForcingSource.CONSTANT

    intensity: us.UnitfulIntensity

    def to_dataframe(self, time_frame: TimeFrame) -> pd.DataFrame:
        time = pd.date_range(
            start=time_frame.start_time,
            end=time_frame.end_time,
            freq=time_frame.time_step,
            name="time",
        )
        values = [self.intensity.value for _ in range(len(time))]
        return pd.DataFrame(data=values, index=time)


class RainfallSynthetic(IRainfall):
    source: ForcingSource = ForcingSource.SYNTHETIC
    timeseries: SyntheticTimeseries

    def to_dataframe(self, time_frame: TimeFrame) -> pd.DataFrame:
        return TimeseriesFactory.from_object(self.timeseries).to_dataframe(
            time_frame=time_frame
        )


class RainfallMeteo(IRainfall):
    source: ForcingSource = ForcingSource.METEO
    precip_units: us.UnitTypesIntensity = us.UnitTypesIntensity.mm_hr
    wind_units: us.UnitTypesVelocity = us.UnitTypesVelocity.mps


class RainfallTrack(IRainfall):
    source: ForcingSource = ForcingSource.TRACK

    path: Annotated[Path, validate_file_extension([".cyc", ".spw"])]

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        if self.path:
            self.path = copy_file_to_output_dir(self.path, Path(output_dir))


class RainfallCSV(IRainfall):
    source: ForcingSource = ForcingSource.CSV

    path: Annotated[Path, validate_file_extension([".csv"])]

    units: us.UnitTypesIntensity = us.UnitTypesIntensity.mm_hr

    def to_dataframe(self, time_frame: TimeFrame) -> pd.DataFrame:
        return CSVTimeseries.load_file(
            path=self.path, units=us.UnitfulIntensity(value=0, units=self.units)
        ).to_dataframe(time_frame=time_frame)

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        self.path = copy_file_to_output_dir(self.path, Path(output_dir))


class RainfallNetCDF(IRainfall):
    source: ForcingSource = ForcingSource.NETCDF
    units: us.UnitTypesIntensity = us.UnitTypesIntensity.mm_hr

    path: Annotated[Path, validate_file_extension([".nc"])]

    def read(self) -> xr.Dataset:
        required_vars = ("precip",)
        required_coords = ("time", "lat", "lon")
        with xr.open_dataset(self.path) as ds:
            validated_ds = validate_netcdf_forcing(ds, required_vars, required_coords)
        return validated_ds

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        self.path = copy_file_to_output_dir(self.path, Path(output_dir))
