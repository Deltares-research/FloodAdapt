import os
from pathlib import Path
from typing import Annotated

import pandas as pd

from flood_adapt.misc.utils import (
    copy_file_to_output_dir,
    validate_file_extension,
)
from flood_adapt.objects.forcing import unit_system as us
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

    path: Annotated[Path, validate_file_extension([".csv"])]

    units: us.UnitTypesDischarge = us.UnitTypesDischarge.cms

    def to_dataframe(self, time_frame: TimeFrame) -> pd.DataFrame:
        return CSVTimeseries.load_file(
            path=self.path, units=us.UnitfulDischarge(value=0, units=self.units)
        ).to_dataframe(time_frame=time_frame)

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        self.path = copy_file_to_output_dir(self.path, Path(output_dir))
