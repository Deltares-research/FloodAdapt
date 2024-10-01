import os
import shutil
from datetime import datetime
from pathlib import Path
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
    DEFAULT_TIMESTEP,
    REFERENCE_TIME,
    ForcingSource,
)
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDischarge,
    UnitfulTime,
    UnitTypesDischarge,
    UnitTypesTime,
)


class DischargeConstant(IDischarge):
    _source: ClassVar[ForcingSource] = ForcingSource.CONSTANT
    discharge: UnitfulDischarge

    def get_data(
        self, strict=True, t0: datetime = None, t1: datetime = None
    ) -> pd.DataFrame:
        if t0 is None:
            t0 = REFERENCE_TIME
        elif isinstance(t0, UnitfulTime):
            t0 = REFERENCE_TIME + t0.to_timedelta()

        if t1 is None:
            t1 = t0 + UnitfulTime(value=1, units=UnitTypesTime.hours).to_timedelta()
        elif isinstance(t1, UnitfulTime):
            t1 = t0 + t1.to_timedelta()

        time = pd.date_range(start=t0, end=t1, freq=DEFAULT_TIMESTEP.to_timedelta())
        data = {"data_0": [self.discharge.value for _ in range(len(time))]}
        return pd.DataFrame(data=data, index=time)

    @classmethod
    def default(cls) -> "DischargeConstant":
        return cls(discharge=UnitfulDischarge(value=0, units=UnitTypesDischarge.cms))


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

    @staticmethod
    def default() -> "DischargeSynthetic":
        return DischargeSynthetic(
            timeseries=SyntheticTimeseriesModel.default(UnitfulDischarge)
        )


class DischargeFromCSV(IDischarge):
    _source: ClassVar[ForcingSource] = ForcingSource.CSV

    path: str | os.PathLike | Path

    def get_data(
        self, strict=True, t0: datetime = None, t1: datetime = None
    ) -> pd.DataFrame:
        if t0 is None:
            t0 = REFERENCE_TIME
        elif isinstance(t0, UnitfulTime):
            t0 = REFERENCE_TIME + t0.to_timedelta()

        if t1 is None:
            t1 = t0 + UnitfulTime(value=1, units=UnitTypesTime.hours).to_timedelta()
        elif isinstance(t1, UnitfulTime):
            t1 = t0 + t1.to_timedelta()

        try:
            return CSVTimeseries.load_file(path=self.path).to_dataframe(
                start_time=t0, end_time=t1
            )

        except Exception as e:
            if strict:
                raise
            else:
                self._logger.error(f"Error reading CSV file: {self.path}. {e}")

    def save_additional(self, path: str | os.PathLike):
        if self.path:
            shutil.copy2(self.path, path)

    @staticmethod
    def default() -> "DischargeFromCSV":
        return DischargeFromCSV(path="path/to/discharge.csv")
