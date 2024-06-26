import pandas as pd
from pandas.core.api import DataFrame as DataFrame

from flood_adapt.object_model.hazard.new_events.forcing.forcing import (
    ForcingType,
    IForcing,
)
from flood_adapt.object_model.hazard.new_events.timeseries import (
    SyntheticTimeseries,
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.io.unitfulvalue import UnitfulIntensity


class IRainfall(IForcing):
    _type = ForcingType.RAINFALL


class RainfallConstant(IRainfall):
    intensity: UnitfulIntensity

    def get_data(self) -> DataFrame:
        return pd.DataFrame(
            {
                "intensity": [self.intensity.value],
                "time": [0],
            }
        )


class RainfallSynthetic(IRainfall):
    timeseries: SyntheticTimeseriesModel

    def get_data(self) -> DataFrame:
        return DataFrame(
            SyntheticTimeseries().load_dict(self.timeseries).calculate_data()
        )


class RainfallFromModel(IRainfall):
    path: str


class RainfallFromSPWFile(IRainfall):
    path: str


class RainfallFromTrack(IRainfall):
    path: str
