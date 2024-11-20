import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar, Optional

import pandas as pd

from flood_adapt.object_model.hazard.event.timeseries import (
    CSVTimeseries,
    SyntheticTimeseries,
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.hazard.interface.forcing import (
    IDischarge,
)
from flood_adapt.object_model.hazard.interface.models import (
    DEFAULT_TIMESTEP,
    ForcingSource,
)
from flood_adapt.object_model.interface.site import RiverModel
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDischarge,
    UnitTypesDischarge,
)


class DischargeConstant(IDischarge):
    _source: ClassVar[ForcingSource] = ForcingSource.CONSTANT

    discharge: UnitfulDischarge

    def get_data(
        self,
        t0: Optional[datetime] = None,
        t1: Optional[datetime] = None,
        strict: bool = True,
        **kwargs: Any,
    ) -> Optional[pd.DataFrame]:
        t0, t1 = self.parse_time(t0, t1)
        time = pd.date_range(
            start=t0, end=t1, freq=DEFAULT_TIMESTEP.to_timedelta(), name="time"
        )
        data = {self.river.name: [self.discharge.value for _ in range(len(time))]}
        return pd.DataFrame(data=data, index=time)

    @classmethod
    def default(cls) -> "DischargeConstant":
        river = RiverModel(
            name="default_river",
            mean_discharge=UnitfulDischarge(value=0, units=UnitTypesDischarge.cms),
            x_coordinate=0,
            y_coordinate=0,
        )
        return DischargeConstant(
            river=river,
            discharge=UnitfulDischarge(value=0, units=UnitTypesDischarge.cms),
        )


class DischargeSynthetic(IDischarge):
    _source: ClassVar[ForcingSource] = ForcingSource.SYNTHETIC

    timeseries: SyntheticTimeseriesModel

    def get_data(
        self,
        t0: Optional[datetime] = None,
        t1: Optional[datetime] = None,
        strict: bool = True,
        **kwargs: Any,
    ) -> Optional[pd.DataFrame]:
        discharge = SyntheticTimeseries.load_dict(data=self.timeseries)

        if t1 is None:
            t0, t1 = self.parse_time(t0, discharge.attrs.duration)
        else:
            t0, t1 = self.parse_time(t0, t1)

        try:
            df = discharge.to_dataframe(start_time=t0, end_time=t1)
            df.columns = [self.river.name]
            return df
        except Exception as e:
            if strict:
                raise
            else:
                self.logger.error(f"Error loading synthetic discharge timeseries: {e}")

    @classmethod
    def default(cls) -> "DischargeSynthetic":
        river = RiverModel(
            name="default_river",
            mean_discharge=UnitfulDischarge(value=0, units=UnitTypesDischarge.cms),
            x_coordinate=0,
            y_coordinate=0,
        )
        return DischargeSynthetic(
            river=river,
            timeseries=SyntheticTimeseriesModel.default(UnitfulDischarge),
        )


class DischargeCSV(IDischarge):
    _source: ClassVar[ForcingSource] = ForcingSource.CSV

    path: Path

    def get_data(
        self,
        t0: Optional[datetime] = None,
        t1: Optional[datetime] = None,
        strict: bool = True,
        **kwargs: Any,
    ) -> Optional[pd.DataFrame]:
        t0, t1 = self.parse_time(t0, t1)

        try:
            return CSVTimeseries.load_file(path=self.path).to_dataframe(
                start_time=t0, end_time=t1
            )

        except Exception as e:
            if strict:
                raise
            else:
                self.logger.error(f"Error reading CSV file: {self.path}. {e}")

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        if self.path:
            output_dir = Path(output_dir)
            if self.path == output_dir / self.path.name:
                return
            output_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.path, output_dir)
            self.path = output_dir / self.path.name

    @classmethod
    def default(cls) -> "DischargeCSV":
        river = RiverModel(
            name="default_river",
            mean_discharge=UnitfulDischarge(value=0, units=UnitTypesDischarge.cms),
            x_coordinate=0,
            y_coordinate=0,
        )
        return DischargeCSV(river=river, path="path/to/discharge.csv")
