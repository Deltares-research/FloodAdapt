import os

import pandas as pd
import xarray as xr
from pydantic import Field

from flood_adapt.object_model.hazard.event.timeseries import (
    SyntheticTimeseries,
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.hazard.interface.events import TimeModel
from flood_adapt.object_model.hazard.interface.forcing import (
    IRainfall,
)
from flood_adapt.object_model.hazard.interface.models import (
    ForcingSource,
)
from flood_adapt.object_model.interface.site import SiteModel
from flood_adapt.object_model.io.unitfulvalue import UnitfulIntensity
from flood_adapt.object_model.hazard.event.meteo import read_meteo

class RainfallConstant(IRainfall):
    _source = ForcingSource.CONSTANT

    intensity: UnitfulIntensity


class RainfallSynthetic(IRainfall):
    _source = ForcingSource.SYNTHETIC
    timeseries: SyntheticTimeseriesModel

    def get_data(self) -> pd.DataFrame:
        return pd.DataFrame(
            SyntheticTimeseries().load_dict(self.timeseries).calculate_data()
        )


class RainfallFromMeteo(IRainfall):
    _source = ForcingSource.METEO
    path: str | os.PathLike | None = Field(default=None)
    # path to the meteo data, set this when downloading it

    def get_data(self) -> xr.DataArray:
        if self.path is None:
            raise ValueError(
                "Meteo path is not set. Download the meteo dataset first using HistoricalEvent.download_meteo().."
            )
        
        return read_meteo(meteo_dir=self.path)[
            "precip"
        ]  # use `.to_dataframe()` to convert to pd.DataFrame


class RainfallFromTrack(IRainfall):
    _source = ForcingSource.TRACK

    path: str | os.PathLike | None = Field(default=None)
    # path to spw file, set this when creating it

    def get_data(self) -> pd.DataFrame:
        return self.path  # TODO implement
