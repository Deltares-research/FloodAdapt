import os
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
from flood_adapt.object_model.hazard.interface.models import ForcingSource
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDischarge,
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

    def get_data(self, strict=True) -> pd.DataFrame:
        try:
            return pd.DataFrame(
                SyntheticTimeseries().load_dict(self.timeseries).calculate_data()
            )
        except Exception as e:
            if strict:
                raise
            else:
                self._logger.error(f"Error loading synthetic discharge timeseries: {e}")

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

    @classmethod
    def default(cls) -> "DischargeFromCSV":
        return DischargeFromCSV(path="path/to/discharge.csv")
