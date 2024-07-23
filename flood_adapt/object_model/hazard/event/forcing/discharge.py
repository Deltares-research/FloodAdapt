import os

import pandas as pd
from pandas.core.api import DataFrame as DataFrame

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
    _source = ForcingSource.CONSTANT
    discharge: UnitfulDischarge


class DischargeSynthetic(IDischarge):
    _source = ForcingSource.SYNTHETIC

    timeseries: SyntheticTimeseriesModel

    def get_data(self) -> DataFrame:
        return pd.DataFrame(
            SyntheticTimeseries().load_dict(self.timeseries).calculate_data()
        )


class DischargeFromCSV(IDischarge):
    _source = ForcingSource.CSV

    path: str | os.PathLike

    def get_data(self) -> DataFrame:
        return pd.DataFrame(CSVTimeseries.load_file(self.path).calculate_data())
