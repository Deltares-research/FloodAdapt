import math
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel

from flood_adapt.misc.config import Settings
from flood_adapt.object_model.hazard.event.tide_gauge import TideGauge
from flood_adapt.object_model.hazard.event.timeseries import (
    CSVTimeseries,
    SyntheticTimeseries,
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.hazard.interface.forcing import IWaterlevel
from flood_adapt.object_model.hazard.interface.models import (
    DEFAULT_TIMESTEP,
    REFERENCE_TIME,
    ForcingSource,
    TimeModel,
)
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.interface.site import Site
from flood_adapt.object_model.io import unit_system as us


class SurgeModel(BaseModel):
    """BaseModel describing the expected variables and data types for harmonic tide parameters of synthetic model."""

    timeseries: SyntheticTimeseriesModel


class TideModel(BaseModel):
    """BaseModel describing the expected variables and data types for harmonic tide parameters of synthetic model."""

    harmonic_amplitude: us.UnitfulLength
    harmonic_period: us.UnitfulTime
    harmonic_phase: us.UnitfulTime

    def to_dataframe(
        self, t0: datetime, t1: datetime, ts=DEFAULT_TIMESTEP
    ) -> pd.DataFrame:
        index = pd.date_range(start=t0, end=t1, freq=ts.to_timedelta(), name="time")
        seconds = np.arange(len(index)) * ts.convert(us.UnitTypesTime.seconds)

        amp = self.harmonic_amplitude.value
        omega = 2 * math.pi / (self.harmonic_period.convert(us.UnitTypesTime.seconds))
        phase_seconds = self.harmonic_phase.convert(us.UnitTypesTime.seconds)

        tide = amp * np.cos(omega * (seconds - phase_seconds))  # / 86400
        return pd.DataFrame(data=tide, index=index)


class WaterlevelSynthetic(IWaterlevel):
    _source: ClassVar[ForcingSource] = ForcingSource.SYNTHETIC

    surge: SurgeModel
    tide: TideModel

    def get_data(
        self,
        t0: Optional[datetime] = None,
        t1: Optional[datetime] = None,
        strict: bool = True,
        **kwargs: Any,
    ) -> Optional[pd.DataFrame]:
        surge = SyntheticTimeseries().load_dict(data=self.surge.timeseries)
        if t1 is None:
            t0, t1 = self.parse_time(t0, surge.attrs.duration)
        else:
            t0, t1 = self.parse_time(t0, t1)

        surge_df = surge.to_dataframe(
            start_time=t0,
            end_time=t1,
        )
        # Calculate Surge time series
        start_surge = REFERENCE_TIME + surge.attrs.start_time.to_timedelta()
        end_surge = start_surge + surge.attrs.duration.to_timedelta()

        surge_ts = surge.calculate_data()
        time_surge = pd.date_range(
            start=start_surge,
            end=end_surge,
            freq=DEFAULT_TIMESTEP.to_timedelta(),
            name="time",
        )

        surge_df = pd.DataFrame(surge_ts, index=time_surge)
        tide_df = self.tide.to_dataframe(t0, t1)

        # Reindex the shorter DataFrame to match the longer one
        surge_df = surge_df.reindex(tide_df.index).fillna(0)

        # Combine
        wl_df = tide_df.add(surge_df, axis="index")
        wl_df.columns = ["data_0"]

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
    _source: ClassVar[ForcingSource] = ForcingSource.CSV

    path: Path

    def get_data(self, t0=None, t1=None, strict=True, **kwargs) -> pd.DataFrame:
        t0, t1 = self.parse_time(t0, t1)
        try:
            return CSVTimeseries.load_file(path=self.path).to_dataframe(
                start_time=t0, end_time=t1
            )
        except Exception as e:
            if strict:
                raise
            else:
                self.logger.error(f"Error reading CSV file: {self.path}. {e}")

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
    _source: ClassVar[ForcingSource] = ForcingSource.MODEL

    def get_data(
        self,
        t0=None,
        t1=None,
        strict=True,
        scenario: Optional[IScenario] = None,
        **kwargs,
    ) -> pd.DataFrame:
        from flood_adapt.adapter.sfincs_offshore import OffshoreSfincsHandler

        if scenario is None:
            raise ValueError(
                "Scenario is not set. Provide a scenario to run the offshore model."
            )

        try:
            return OffshoreSfincsHandler().get_resulting_waterlevels(scenario=scenario)
        except Exception as e:
            if strict:
                raise
            else:
                self.logger.error(
                    f"Error reading model results: {kwargs.get('scenario', None)}. {e}"
                )

    @classmethod
    def default(cls) -> "WaterlevelModel":
        return WaterlevelModel()


class WaterlevelGauged(IWaterlevel):
    _source: ClassVar[ForcingSource] = ForcingSource.GAUGED

    def get_data(
        self, t0=None, t1=None, strict=True, **kwargs
    ) -> Optional[pd.DataFrame]:
        t0, t1 = self.parse_time(t0, t1)
        time = TimeModel(start_time=t0, end_time=t1)

        site = Site.load_file(
            Settings().database_path / "static" / "site" / "site.toml"
        )
        if site.attrs.tide_gauge is None:
            raise ValueError("No tide gauge defined for this site.")

        try:
            return TideGauge(site.attrs.tide_gauge).get_waterlevels_in_time_frame(time)
        except Exception as e:
            if strict:
                raise e
            else:
                self.logger.error(f"Error reading gauge data: {e}")
                return None

    @classmethod
    def default(cls) -> "WaterlevelGauged":
        return WaterlevelGauged()
