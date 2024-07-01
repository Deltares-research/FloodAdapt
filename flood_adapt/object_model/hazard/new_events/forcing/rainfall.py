import pandas as pd
from pandas.core.api import DataFrame as DataFrame

from flood_adapt.object_model.hazard.new_events.forcing.forcing import (
    ForcingSource,
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
    _source = ForcingSource.CONSTANT

    intensity: UnitfulIntensity

    def get_data(self) -> DataFrame:
        return pd.DataFrame(
            {
                "intensity": [self.intensity.value],
                "time": [0],
            }
        )


class RainfallSynthetic(IRainfall):
    _source = ForcingSource.SYNTHETIC
    timeseries: SyntheticTimeseriesModel

    def get_data(self) -> DataFrame:
        return DataFrame(
            SyntheticTimeseries().load_dict(self.timeseries).calculate_data()
        )


class RainfallFromModel(IRainfall):
    _source = ForcingSource.MODEL
    path: str


class RainfallFromSPWFile(IRainfall):
    _source = ForcingSource.SPW_FILE
    path: str


class RainfallFromTrack(IRainfall):
    _source = ForcingSource.TRACK
    path: str
