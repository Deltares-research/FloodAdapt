import os
from pathlib import Path
from typing import Annotated

import pandas as pd

from flood_adapt.object_model.hazard.forcing.timeseries import (
    CSVTimeseries,
    SyntheticTimeseries,
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    IDischarge,
)
from flood_adapt.object_model.hazard.interface.models import TimeModel
from flood_adapt.object_model.io import unit_system as us
from flood_adapt.object_model.utils import (
    copy_file_to_output_dir,
    validate_file_extension,
)


class DischargeConstant(IDischarge):
    source: ForcingSource = ForcingSource.CONSTANT

    discharge: us.UnitfulDischarge

    def to_dataframe(self, time_frame: TimeModel) -> pd.DataFrame:
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

    timeseries: SyntheticTimeseriesModel[us.UnitfulDischarge]

    def to_dataframe(self, time_frame: TimeModel) -> pd.DataFrame:
        discharge = SyntheticTimeseries(data=self.timeseries)
        df = discharge.to_dataframe(time_frame=time_frame)
        df.columns = [self.river.name]
        return df


class DischargeCSV(IDischarge):
    source: ForcingSource = ForcingSource.CSV

    path: Annotated[Path, validate_file_extension([".csv"])]

    units: us.UnitTypesDischarge = us.UnitTypesDischarge.cms

    def to_dataframe(self, time_frame: TimeModel) -> pd.DataFrame:
        return (
            CSVTimeseries[self.units]
            .load_file(path=self.path)
            .to_dataframe(time_frame=time_frame)
        )

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        self.path = copy_file_to_output_dir(self.path, Path(output_dir))
