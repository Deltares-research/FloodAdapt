import math
import os
import shutil
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


class SurgeModel(BaseModel):
    """BaseModel describing the expected variables and data types for harmonic tide parameters of synthetic model."""

    timeseries: SyntheticTimeseriesModel


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

        amp = self.harmonic_amplitude.value
        omega = 2 * math.pi / (self.harmonic_period.convert(us.UnitTypesTime.seconds))
        phase_seconds = self.harmonic_phase.convert(us.UnitTypesTime.seconds)

        tide = amp * np.cos(omega * (seconds - phase_seconds))  # / 86400
        return pd.DataFrame(data=tide, index=index)


class WaterlevelSynthetic(IWaterlevel):
    source: ForcingSource = ForcingSource.SYNTHETIC

    surge: SurgeModel
    tide: TideModel

    def to_dataframe(self, time_frame: TimeModel) -> pd.DataFrame:
        surge = SyntheticTimeseries().load_dict(data=self.surge.timeseries)
        surge_df = surge.to_dataframe(
            time_frame=time_frame,
        )
        # Calculate Surge time series
        start_surge = time_frame.start_time + surge.attrs.start_time.to_timedelta()
        end_surge = start_surge + surge.attrs.duration.to_timedelta()

        surge_ts = surge.calculate_data()
        time_surge = pd.date_range(
            start=start_surge,
            end=end_surge,
            freq=TimeModel().time_step,
            name="time",
        )

        surge_df = pd.DataFrame(surge_ts, index=time_surge)
        tide_df = self.tide.to_dataframe(time_frame)

        # Reindex the shorter DataFrame to match the longer one
        surge_df = surge_df.reindex(tide_df.index).fillna(0)

        # Combine
        wl_df = tide_df.add(surge_df, axis="index")
        wl_df.columns = ["waterlevel"]

        return wl_df

    @classmethod
    def default(cls) -> "WaterlevelSynthetic":
        return WaterlevelSynthetic(
            surge=SurgeModel(
                timeseries=SyntheticTimeseriesModel.default(us.UnitfulLength)
            ),
            tide=TideModel(
                harmonic_amplitude=us.UnitfulLength(
                    value=0, units=us.UnitTypesLength.meters
                ),
                harmonic_period=us.UnitfulTime(value=0, units=us.UnitTypesTime.seconds),
                harmonic_phase=us.UnitfulTime(value=0, units=us.UnitTypesTime.seconds),
            ),
        )


class WaterlevelCSV(IWaterlevel):
    source: ForcingSource = ForcingSource.CSV

    path: Path

    def to_dataframe(self, time_frame: TimeModel) -> pd.DataFrame:
        return CSVTimeseries.load_file(path=self.path).to_dataframe(
            time_frame=time_frame
        )

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        if self.path:
            output_dir = Path(output_dir)
            if self.path == output_dir / self.path.name:
                return
            output_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.path, output_dir)
            self.path = output_dir / self.path.name

    @classmethod
    def default(cls) -> "WaterlevelCSV":
        return WaterlevelCSV(path="path/to/waterlevel.csv")


class WaterlevelModel(IWaterlevel):
    source: ForcingSource = ForcingSource.MODEL

    @classmethod
    def default(cls) -> "WaterlevelModel":
        return WaterlevelModel()


class WaterlevelGauged(IWaterlevel):
    source: ForcingSource = ForcingSource.GAUGED

    @classmethod
    def default(cls) -> "WaterlevelGauged":
        return WaterlevelGauged()
