import os
import shutil
from pathlib import Path
from typing import Optional

import pandas as pd
from pydantic import Field

from flood_adapt.object_model.hazard.forcing.timeseries import (
    CSVTimeseries,
    SyntheticTimeseries,
)
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    IRainfall,
)
from flood_adapt.object_model.hazard.interface.models import TimeModel
from flood_adapt.object_model.hazard.interface.timeseries import (
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.io import unit_system as us


class RainfallConstant(IRainfall):
    source: ForcingSource = ForcingSource.CONSTANT

    intensity: us.UnitfulIntensity

    def to_dataframe(self, time_frame: TimeModel) -> pd.DataFrame:
        time = pd.date_range(
            start=time_frame.start_time,
            end=time_frame.end_time,
            freq=TimeModel().time_step,
            name="time",
        )
        values = [self.intensity.value for _ in range(len(time))]
        return pd.DataFrame(data=values, index=time)

    @classmethod
    def default(cls) -> "RainfallConstant":
        return cls(
            intensity=us.UnitfulIntensity(value=0, units=us.UnitTypesIntensity.mm_hr)
        )


class RainfallSynthetic(IRainfall):
    source: ForcingSource = ForcingSource.SYNTHETIC
    timeseries: SyntheticTimeseriesModel

    def to_dataframe(self, time_frame: TimeModel) -> pd.DataFrame:
        rainfall = SyntheticTimeseries().load_dict(data=self.timeseries)
        return rainfall.to_dataframe(
            start_time=time_frame.start_time, end_time=time_frame.end_time
        )

    @classmethod
    def default(cls) -> "RainfallSynthetic":
        return RainfallSynthetic(
            timeseries=SyntheticTimeseriesModel.default(us.UnitfulIntensity)
        )


class RainfallMeteo(IRainfall):
    source: ForcingSource = ForcingSource.METEO
    precip_units: us.UnitTypesIntensity = us.UnitTypesIntensity.mm_hr
    wind_units: us.UnitTypesVelocity = us.UnitTypesVelocity.mps

    @classmethod
    def default(cls) -> "RainfallMeteo":
        return RainfallMeteo()


class RainfallTrack(IRainfall):
    source: ForcingSource = ForcingSource.TRACK

    path: Optional[Path] = Field(default=None)
    # path to spw file, set this when creating it

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        if self.path:
            output_dir = Path(output_dir)
            if self.path == output_dir / self.path.name:
                return
            output_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.path, output_dir)
            self.path = output_dir / self.path.name

    @classmethod
    def default(cls) -> "RainfallTrack":
        return RainfallTrack()


class RainfallCSV(IRainfall):
    source: ForcingSource = ForcingSource.CSV

    path: Path
    unit: us.UnitTypesIntensity = us.UnitTypesIntensity.mm_hr

    def to_dataframe(self, time_frame: TimeModel) -> pd.DataFrame:
        return CSVTimeseries.load_file(path=self.path).to_dataframe(
            start_time=time_frame.start_time, end_time=time_frame.end_time
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
    def default(cls) -> "RainfallCSV":
        return RainfallCSV(path="path/to/rainfall.csv")
