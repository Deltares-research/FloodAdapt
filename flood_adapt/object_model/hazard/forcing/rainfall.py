import os
from pathlib import Path
from typing import Annotated

import pandas as pd
import xarray as xr

from flood_adapt.object_model.hazard.forcing.netcdf import validate_netcdf_forcing
from flood_adapt.object_model.hazard.forcing.timeseries import (
    CSVTimeseries,
    SyntheticTimeseries,
)
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    IRainfall,
)
from flood_adapt.object_model.hazard.interface.models import TimeModel
from flood_adapt.object_model.hazard.interface.timeseries import (
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.io import unit_system as us
from flood_adapt.object_model.utils import (
    copy_file_to_output_dir,
    validate_file_extension,
)


class RainfallConstant(IRainfall):
    source: ForcingSource = ForcingSource.CONSTANT

    intensity: us.UnitfulIntensity

    def to_dataframe(self, time_frame: TimeModel) -> pd.DataFrame:
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
    timeseries: (
        SyntheticTimeseriesModel[us.UnitfulIntensity]
        | SyntheticTimeseriesModel[us.UnitfulLength]
    )

    def to_dataframe(self, time_frame: TimeModel) -> pd.DataFrame:
        rainfall = SyntheticTimeseries(data=self.timeseries)
        return rainfall.to_dataframe(time_frame=time_frame)


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

    def to_dataframe(self, time_frame: TimeModel) -> pd.DataFrame:
        return (
            CSVTimeseries[self.units]
            .load_file(path=self.path)
            .to_dataframe(time_frame=time_frame)
        )

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
