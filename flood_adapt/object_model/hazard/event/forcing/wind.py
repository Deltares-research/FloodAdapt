import os

import pandas as pd
import xarray as xr
from pydantic import Field

from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    IWind,
)
from flood_adapt.object_model.io.unitfulvalue import UnitfulDirection, UnitfulVelocity


class WindConstant(IWind):
    _source = ForcingSource.CONSTANT

    speed: UnitfulVelocity
    direction: UnitfulDirection

    def get_data(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "mag": [self.speed.value],
                "dir": [self.direction.value],
            }
        )


class WindSynthetic(IWind):
    pass


class WindFromTrack(IWind):
    pass


class WindFromCSV(IWind):
    _source = ForcingSource.CSV

    path: str | os.PathLike

    def get_data(self) -> pd.DataFrame:
        df = pd.read_csv(
            self.path,
            index_col=0,
            header=None,
        )
        df.index = pd.DatetimeIndex(df.index)
        return df


class WindFromModel(IWind):
    _source = ForcingSource.MODEL

    path: str | os.PathLike | None = Field(default=None)
    # simpath of the offshore model, set this when running the offshore model

    # Required variables: ['wind_u' (m/s), 'wind_v' (m/s)]
    # Required coordinates: ['time', 'mag', 'dir']

    def get_data(self) -> xr.DataArray:
        if self.path is None:
            raise ValueError(
                "Model path is not set. First, download the meteo data using event.process() method."
            )

        from flood_adapt.object_model.hazard.event.historical import HistoricalEvent

        # ASSUMPTION: the download has been done already, see HistoricalEvent.download_meteo().
        # TODO add to read_meteo to run download if not already downloaded.
        return HistoricalEvent.read_meteo(self.path)[
            "wind"
        ]  # use `.to_dataframe()` to convert to pd.DataFrame


class WindFromSPWFile(IWind):
    _source = ForcingSource.SPW_FILE

    path: str | os.PathLike | None = Field(default=None)
    # path to spw file, set this when creating it

    def get_data(self) -> pd.DataFrame:
        return self.path
