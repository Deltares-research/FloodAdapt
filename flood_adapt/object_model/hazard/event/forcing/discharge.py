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
from flood_adapt.object_model.io.unitfulvalue import UnitfulDischarge


class DischargeConstant(IDischarge):
    _source: ClassVar[ForcingSource] = ForcingSource.CONSTANT
    discharge: UnitfulDischarge

    @classmethod
    def default(cls) -> "DischargeConstant":
        return DischargeConstant(discharge=UnitfulDischarge(value=0, units="m3/s"))


class DischargeSynthetic(IDischarge):
    _source: ClassVar[ForcingSource] = ForcingSource.SYNTHETIC

    timeseries: SyntheticTimeseriesModel

    def get_data(self) -> pd.DataFrame:
        return pd.DataFrame(
            SyntheticTimeseries().load_dict(self.timeseries).calculate_data()
        )

    @classmethod
    def default(cls) -> "DischargeSynthetic":
        return DischargeSynthetic(timeseries=SyntheticTimeseriesModel().default())


class DischargeFromCSV(IDischarge):
    _source: ClassVar[ForcingSource] = ForcingSource.CSV

    path: str | os.PathLike

    def get_data(self) -> pd.DataFrame:
        return pd.DataFrame(CSVTimeseries.load_file(self.path).calculate_data())

    @classmethod
    def default(cls) -> "DischargeFromCSV":
        return DischargeFromCSV(path="path/to/discharge.csv")
