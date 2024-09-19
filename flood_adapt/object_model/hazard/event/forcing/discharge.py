import os
import shutil
from datetime import datetime
from typing import ClassVar

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
    REFERENCE_TIME,
    ForcingSource,
)
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDischarge,
    UnitfulTime,
    UnitTypesDischarge,
)


class DischargeConstant(IDischarge):
    _source: ClassVar[ForcingSource] = ForcingSource.CONSTANT
    discharge: UnitfulDischarge

    @classmethod
    def default(cls) -> "DischargeConstant":
        return DischargeConstant(
            discharge=UnitfulDischarge(value=0, units=UnitTypesDischarge.cms)
        )


class DischargeSynthetic(IDischarge):
    _source: ClassVar[ForcingSource] = ForcingSource.SYNTHETIC

    timeseries: SyntheticTimeseriesModel

    def get_data(
        self, strict=True, t0: datetime = None, t1: datetime = None
    ) -> pd.DataFrame:
        discharge = SyntheticTimeseries().load_dict(data=self.timeseries)

        if t0 is None:
            t0 = REFERENCE_TIME
        elif isinstance(t0, UnitfulTime):
            t0 = REFERENCE_TIME + t0.to_timedelta()

        if t1 is None:
            t1 = t0 + discharge.attrs.duration.to_timedelta()
        elif isinstance(t1, UnitfulTime):
            t1 = t0 + t1.to_timedelta()

        try:
            return discharge.to_dataframe(start_time=t0, end_time=t1)
        except Exception as e:
            if strict:
                raise
            else:
                self._logger.error(f"Error loading synthetic rainfall timeseries: {e}")

    @classmethod
    def default(cls) -> "DischargeSynthetic":
        return DischargeSynthetic(
            timeseries=SyntheticTimeseriesModel.default(UnitfulDischarge)
        )


class DischargeFromCSV(IDischarge):
    _source: ClassVar[ForcingSource] = ForcingSource.CSV

    path: str | os.PathLike

    def get_data(self, strict=True) -> pd.DataFrame:
        try:
            return pd.DataFrame(
                CSVTimeseries.load_file(path=self.path).calculate_data()
            )
        except Exception as e:
            if strict:
                raise
            else:
                self._logger.error(f"Error reading CSV file: {self.path}. {e}")

    def save_additional(self, path: str | os.PathLike):
        if self.path:
            shutil.copy2(self.path, path)

    @classmethod
    def default(cls) -> "DischargeFromCSV":
        return DischargeFromCSV(path="path/to/discharge.csv")
