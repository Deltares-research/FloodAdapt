import os

import pandas as pd
import xarray as xr
from pydantic import Field

from flood_adapt.object_model.hazard.event.timeseries import (
    SyntheticTimeseries,
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    IRainfall,
)
from flood_adapt.object_model.io.unitfulvalue import UnitfulIntensity


class RainfallConstant(IRainfall):
    _source = ForcingSource.CONSTANT

    intensity: UnitfulIntensity

    def get_data(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "intensity": [self.intensity.value],
                "time": [0],
            }
        )


class RainfallSynthetic(IRainfall):
    _source = ForcingSource.SYNTHETIC
    timeseries: SyntheticTimeseriesModel

    def get_data(self) -> pd.DataFrame:
        return pd.DataFrame(
            SyntheticTimeseries().load_dict(self.timeseries).calculate_data()
        )


class RainfallFromModel(IRainfall):
    _source = ForcingSource.MODEL
    path: str | os.PathLike | None = Field(default=None)
    # simpath of the offshore model, set this when running the offshore model

    def get_data(self) -> xr.DataArray:
        if self.path is None:
            raise ValueError(
                "Model path is not set. Run the offshore model first using event.process() method."
            )

        from flood_adapt.object_model.hazard.event.historical import HistoricalEvent

        # ASSUMPTION: the download has been done already, see HistoricalEvent.download_meteo().
        # TODO add to read_meteo to run download if not already downloaded.
        return HistoricalEvent.read_meteo(self.path)[
            "precip"
        ]  # use `.to_dataframe()` to convert to pd.DataFrame


class RainfallFromSPWFile(IRainfall):
    _source = ForcingSource.SPW_FILE

    path: str | os.PathLike | None = Field(default=None)
    # path to spw file, set this when creating it

    def get_data(self) -> pd.DataFrame:
        return self.path
