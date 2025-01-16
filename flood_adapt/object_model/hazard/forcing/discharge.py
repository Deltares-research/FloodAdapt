import os
import shutil
from pathlib import Path

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


class DischargeConstant(IDischarge):
    source: ForcingSource = ForcingSource.CONSTANT

    discharge: us.UnitfulDischarge

    def to_dataframe(self, time_frame: TimeModel) -> pd.DataFrame:
        time = pd.date_range(
            start=time_frame.start_time,
            end=time_frame.end_time,
            freq=TimeModel().time_step,
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

    path: Path
    unit: us.UnitTypesDischarge = us.UnitTypesDischarge.cms

    def to_dataframe(self, time_frame: TimeModel) -> pd.DataFrame:
        return CSVTimeseries.load_file(path=self.path).to_dataframe(
            time_frame=time_frame
        )

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        if self.path:
            output_dir = Path(output_dir)
            if self.path == output_dir / self.path.name:
                return
            output_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.path, output_dir)
            self.path = output_dir / self.path.name
