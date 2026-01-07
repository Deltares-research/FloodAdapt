import os
from pathlib import Path
from typing import Annotated, Any

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
    track: CycloneTrackContainer

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        self.track.write(output_dir=Path(output_dir))

    def read(self, directory: Path | None = None, **kwargs) -> None:
        self.track.read(directory=directory, **kwargs)


class WindCSV(IWind):
    source: ForcingSource = ForcingSource.CSV

    path: Annotated[Path | None, validate_file_extension([".csv"])] = None  # DEPRECATED
    timeseries: DataFrameContainer

    units: dict[str, Any] = {
        "speed": us.UnitTypesVelocity.mps,
        "direction": us.UnitTypesDirection.degrees,
    }

    def to_dataframe(self, time_frame: TimeFrame) -> pd.DataFrame:
        ts = CSVTimeseries(
            path=self.timeseries.path,
            units=us.UnitfulVelocity(value=0, units=self.units["speed"]),
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
            self.timeseries = DataFrameContainer(path=self.path, name="wind")
        return self

    def model_dump(self, **kwargs):
        return super().model_dump(exclude={"path"}, **kwargs)


class WindMeteo(IWind):
    source: ForcingSource = ForcingSource.METEO


class WindNetCDF(IWind):
    source: ForcingSource = ForcingSource.NETCDF
    units: us.UnitTypesVelocity = us.UnitTypesVelocity.mps
    path: Annotated[Path | None, validate_file_extension([".nc"])] = None  # DEPRECATED
    timeseries: NetCDFContainer

    def read(self, directory: Path | None = None, **kwargs) -> None:
        self.timeseries.read(directory=directory, **kwargs)
        required_vars = ("wind10_v", "wind10_u", "press_msl")
        required_coords = ("time", "lat", "lon")
        validated_ds = validate_netcdf_forcing(
            self.timeseries.data, required_vars, required_coords
        )
        self.timeseries.set_data(validated_ds)

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        self.timeseries.write(output_dir=output_dir)

    @model_validator(mode="after")
    def convert_path_to_timeseries(self):
        if self.path:
            self.timeseries = NetCDFContainer(path=self.path, name="wind")
        return self

    def model_dump(self, **kwargs):
        return super().model_dump(exclude={"path"}, **kwargs)
