import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
from pydantic import BaseModel

from flood_adapt.object_model.hazard.forcing.timeseries import (
    CSVTimeseries,
    SyntheticTimeseries,
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    IWaterlevel,
)
from flood_adapt.object_model.hazard.interface.models import (
    TimeModel,
)
from flood_adapt.object_model.io import unit_system as us
from flood_adapt.object_model.utils import copy_file_to_output_dir


class SurgeModel(BaseModel):
    """BaseModel describing the expected variables and data types for harmonic tide parameters of synthetic model."""

    timeseries: SyntheticTimeseriesModel[us.UnitfulLength]


class TideModel(BaseModel):
    """BaseModel describing the expected variables and data types for harmonic tide parameters of synthetic model."""

    harmonic_amplitude: us.UnitfulLength
    harmonic_phase: us.UnitfulTime
    harmonic_period: us.UnitfulTime = us.UnitfulTime(
        value=12.4, units=us.UnitTypesTime.hours
    )

    def to_dataframe(self, time_frame: TimeModel) -> pd.DataFrame:
        index = pd.date_range(
            start=time_frame.start_time,
            end=time_frame.end_time,
            freq=time_frame.time_step,
            name="time",
        )
        seconds = np.arange(len(index)) * time_frame.time_step.total_seconds()
        seconds.round(decimals=0)

        amp = self.harmonic_amplitude.value
        omega = 2 * math.pi / (self.harmonic_period.convert(us.UnitTypesTime.seconds))
        phase_seconds = self.harmonic_phase.convert(us.UnitTypesTime.seconds)

        tide = amp * np.cos(omega * (seconds - phase_seconds))
        return pd.DataFrame(data=tide, index=index)


class WaterlevelSynthetic(IWaterlevel):
    source: ForcingSource = ForcingSource.SYNTHETIC

    surge: SurgeModel
    tide: TideModel

    def to_dataframe(self, time_frame: TimeModel) -> pd.DataFrame:
        tide_df = self.tide.to_dataframe(time_frame=time_frame)
        surge = SyntheticTimeseries(data=self.surge.timeseries)
        surge_df = surge.to_dataframe(time_frame=time_frame)

        # Combine
        tide_df.columns = ["waterlevel"]
        surge_df.columns = ["waterlevel"]
        surge_df = surge_df.reindex(tide_df.index, method="nearest", limit=1).fillna(
            value=surge.attrs.fill_value
        )

        wl_df = tide_df.add(surge_df, axis="index", fill_value=0)
        wl_df.columns = ["waterlevel"]

        return wl_df


class WaterlevelCSV(IWaterlevel):
    source: ForcingSource = ForcingSource.CSV

    path: Path
    units: us.UnitTypesLength = us.UnitTypesLength.meters

    def to_dataframe(self, time_frame: TimeModel) -> pd.DataFrame:
        return (
            CSVTimeseries[self.units]
            .load_file(path=self.path)
            .to_dataframe(time_frame=time_frame)
        )

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        self.path = copy_file_to_output_dir(self.path, Path(output_dir))


class WaterlevelModel(IWaterlevel):
    source: ForcingSource = ForcingSource.MODEL


class WaterlevelGauged(IWaterlevel):
    source: ForcingSource = ForcingSource.GAUGED
