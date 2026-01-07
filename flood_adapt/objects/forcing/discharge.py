import os
from pathlib import Path
from typing import Annotated

import pandas as pd
from pydantic import model_validator

from flood_adapt.misc.utils import validate_file_extension
from flood_adapt.objects import unit_system as us
from flood_adapt.objects.data_container import DataFrameContainer
from flood_adapt.objects.forcing.forcing import (
    ForcingSource,
    IDischarge,
)
from flood_adapt.objects.forcing.time_frame import TimeFrame
from flood_adapt.objects.forcing.timeseries import (
    CSVTimeseries,
    SyntheticTimeseries,
    TimeseriesFactory,
)


class DischargeConstant(IDischarge):
    source: ForcingSource = ForcingSource.CONSTANT

    discharge: us.UnitfulDischarge

    def to_dataframe(self, time_frame: TimeFrame) -> pd.DataFrame:
        time = pd.date_range(
            start=time_frame.start_time,
            end=time_frame.end_time,
            freq=time_frame.time_step,
            name="time",
        )
        data = [self.discharge.value for _ in range(len(time))]
        return pd.DataFrame(index=time, data=data, columns=[self.river.name])


class DischargeSynthetic(IDischarge):
    source: ForcingSource = ForcingSource.SYNTHETIC

    timeseries: SyntheticTimeseries

    def to_dataframe(self, time_frame: TimeFrame) -> pd.DataFrame:
        df = TimeseriesFactory.from_object(self.timeseries).to_dataframe(
            time_frame=time_frame
        )
        df.columns = [self.river.name]
        return df


class DischargeCSV(IDischarge):
    source: ForcingSource = ForcingSource.CSV

    path: Annotated[Path | None, validate_file_extension([".csv"])] = None  # DEPRECATED
    timeseries: DataFrameContainer

    units: us.UnitTypesDischarge = us.UnitTypesDischarge.cms

    def to_dataframe(self, time_frame: TimeFrame) -> pd.DataFrame:
        ts = CSVTimeseries(
            path=self.timeseries.path,
            units=us.UnitfulDischarge(value=0, units=self.units),
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
            self.timeseries = DataFrameContainer(path=self.path, name=self.river.name)
        return self

    def model_dump(self, **kwargs):
        return super().model_dump(exclude={"path"}, **kwargs)
