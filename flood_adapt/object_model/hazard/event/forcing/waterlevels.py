import math
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

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
    ShapeType,
    TimeModel,
)
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulLength,
    UnitfulTime,
    UnitTypesLength,
    UnitTypesTime,
)
from flood_adapt.object_model.site import Site


class SurgeModel(BaseModel):
    """BaseModel describing the expected variables and data types for harmonic tide parameters of synthetic model."""

    timeseries: SyntheticTimeseriesModel


class TideModel(BaseModel):
    """BaseModel describing the expected variables and data types for harmonic tide parameters of synthetic model."""

    harmonic_amplitude: UnitfulLength
    harmonic_period: UnitfulTime
    harmonic_phase: UnitfulTime

    def to_timeseries_model(self) -> SyntheticTimeseriesModel:
        return SyntheticTimeseriesModel(
            shape_type=ShapeType.harmonic,
            duration=self.harmonic_period,
            peak_time=self.harmonic_phase,
            peak_value=self.harmonic_amplitude,
        )

    def to_dataframe(
        self, t0: datetime, t1: datetime, ts=DEFAULT_TIMESTEP
    ) -> pd.DataFrame:
        index = pd.date_range(start=t0, end=t1, freq=ts.to_timedelta(), name="time")
        seconds = np.arange(len(index)) * ts.convert("seconds")

        amp = self.harmonic_amplitude.value
        omega = 2 * math.pi / (self.harmonic_period.convert("seconds"))
        phase_seconds = self.harmonic_phase.convert("seconds")

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
        tide_df = self.tide.to_dataframe(t0, t1)  # + msl + slr

        # Reindex the shorter DataFrame to match the longer one
        surge_df = surge_df.reindex(tide_df.index).fillna(0)

        # Combine
        wl_df = tide_df.add(surge_df, axis="index")
        wl_df.columns = ["data_0"]

        return wl_df

    @staticmethod
    def default() -> "WaterlevelSynthetic":
        return WaterlevelSynthetic(
            surge=SurgeModel(
                timeseries=SyntheticTimeseriesModel.default(UnitfulLength)
            ),
            tide=TideModel(
                harmonic_amplitude=UnitfulLength(value=0, units=UnitTypesLength.meters),
                harmonic_period=UnitfulTime(value=0, units=UnitTypesTime.seconds),
                harmonic_phase=UnitfulTime(value=0, units=UnitTypesTime.seconds),
            ),
        )


class WaterlevelFromCSV(IWaterlevel):
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
                self._logger.error(f"Error reading CSV file: {self.path}. {e}")

    def save_additional(self, toml_dir: Path):
        if self.path:
            shutil.copy2(self.path, toml_dir)
            self.path = (
                toml_dir / self.path.name
            )  # update the path to the new location so the toml also gets updated

    @staticmethod
    def default() -> "WaterlevelFromCSV":
        return WaterlevelFromCSV(path="path/to/waterlevel.csv")


class WaterlevelFromModel(IWaterlevel):
    _source: ClassVar[ForcingSource] = ForcingSource.MODEL

    path: Optional[Path] = Field(default=None)
    # simpath of the offshore model, set this when running the offshore model

    def get_data(self, t0=None, t1=None, strict=True, **kwargs) -> pd.DataFrame:
        # Note that this does not run the offshore simulation, it only tries to read the results from the model.
        # Running the model is done in the process method of the event.
        try:
            if self.path is None:
                raise ValueError(
                    "Model path is not set. Run the offshore model first using event.process() method."
                )

            from flood_adapt.integrator.sfincs_adapter import SfincsAdapter

            with SfincsAdapter(model_root=self.path) as _offshore_model:
                return _offshore_model._get_wl_df_from_offshore_his_results()
        except Exception as e:
            if strict:
                raise
            else:
                self._logger.error(f"Error reading model results: {self.path}. {e}")

    @staticmethod
    def default() -> "WaterlevelFromModel":
        return WaterlevelFromModel()


class WaterlevelFromGauged(IWaterlevel):
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
                self._logger.error(f"Error reading gauge data: {e}")
                return None

    @staticmethod
    def default() -> "WaterlevelFromGauged":
        return WaterlevelFromGauged()
