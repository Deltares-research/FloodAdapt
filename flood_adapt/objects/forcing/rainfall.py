import os
from pathlib import Path
from typing import Annotated

import pandas as pd
from pydantic import model_validator

from flood_adapt.misc.utils import (
    validate_file_extension,
)
from flood_adapt.objects import unit_system as us
from flood_adapt.objects.data_container import (
    CycloneTrackContainer,
    DataFrameContainer,
    NetCDFContainer,
)
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
    # TODO add NetCDFContainer


class RainfallTrack(IRainfall):
    source: ForcingSource = ForcingSource.TRACK
    track: CycloneTrackContainer

    def save_additional(self, output_dir: Path) -> None:
        self.track.write(output_dir=Path(output_dir))

    def read(self, directory: Path | None = None, **kwargs) -> None:
        self.track.read(directory=directory, **kwargs)


class RainfallCSV(IRainfall):
    source: ForcingSource = ForcingSource.CSV

    path: Annotated[Path | None, validate_file_extension([".csv"])] = None  # DEPRECATED
    timeseries: DataFrameContainer

    units: us.UnitTypesIntensity = us.UnitTypesIntensity.mm_hr

    def to_dataframe(self, time_frame: TimeFrame) -> pd.DataFrame:
        ts = CSVTimeseries(
            path=self.timeseries.path,
            units=us.UnitfulIntensity(value=0, units=self.units),
            _data=self.timeseries.data,
        )
        return ts.to_dataframe(time_frame=time_frame)

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        self.timeseries.write(output_dir=output_dir)

    def read(self, directory: Path | None = None, **kwargs) -> None:
        self.timeseries.read(directory=directory, **kwargs)

    @model_validator(mode="after")
    def convert_path_to_timeseries(self):
        if self.path:
            self.timeseries = DataFrameContainer(path=self.path, name="rainfall")
        return self

    def model_dump(self, **kwargs):
        return super().model_dump(exclude={"path"}, **kwargs)


class RainfallNetCDF(IRainfall):
    source: ForcingSource = ForcingSource.NETCDF
    units: us.UnitTypesIntensity = us.UnitTypesIntensity.mm_hr

    path: Annotated[Path | None, validate_file_extension([".nc"])] = None  # DEPRECATED
    timeseries: NetCDFContainer

    def read(self, directory: Path | None = None, **kwargs) -> None:
        self.timeseries.read(directory=directory, **kwargs)
        required_vars = ("precip",)
        required_coords = ("time", "lat", "lon")
        validated_ds = validate_netcdf_forcing(
            self.timeseries.data, required_vars, required_coords
        )
        self.timeseries.set_data(validated_ds)

    def save_additional(self, output_dir: Path | None = None) -> None:
        self.timeseries.write(output_dir=output_dir)

    @model_validator(mode="after")
    def convert_path_to_timeseries(self):
        if self.path:
            self.timeseries = NetCDFContainer(path=self.path, name="rainfall")
        return self

    def model_dump(self, **kwargs):
        return super().model_dump(exclude={"path"}, **kwargs)
