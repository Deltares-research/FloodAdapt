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
from flood_adapt.object_model.io.unitfulvalue import UnitfulDischarge

__all__ = ["DischargeConstant", "DischargeSynthetic", "DischargeFromCSV"]


class DischargeConstant(IDischarge):
    discharge: UnitfulDischarge

    def get_data(self) -> DataFrame:
        return pd.DataFrame(
            {
                "discharge": [self.discharge.value],
                "time": [0],
            }
        )


class DischargeSynthetic(IDischarge):
    timeseries: SyntheticTimeseriesModel

    def get_data(self) -> DataFrame:
        return SyntheticTimeseries().load_dict(self.timeseries).calculate_data()


class DischargeFromCSV(IDischarge):
    path: str

    def get_data(self) -> DataFrame:
        return CSVTimeseries(self.path).calculate_data()
