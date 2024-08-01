import math
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import tomli
import tomli_w

from flood_adapt.object_model.hazard.interface.models import (
    DEFAULT_DATETIME_FORMAT,
    DEFAULT_TIMESTEP,
    MAX_TIDAL_CYCLES,
    REFERENCE_TIME,
    ShapeType,
)
from flood_adapt.object_model.hazard.interface.timeseries import (
    CSVTimeseriesModel,
    ITimeseries,
    ITimeseriesCalculationStrategy,
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulTime,
    UnitTypesTime,
)


### CALCULATION STRATEGIES ###
class ScsTimeseriesCalculator(ITimeseriesCalculationStrategy):
    def calculate(
        self, attrs: SyntheticTimeseriesModel, timestep: UnitfulTime
    ) -> np.ndarray:
        _duration = attrs.duration.convert(UnitTypesTime.seconds)
        _shape_start = attrs.peak_time.convert(UnitTypesTime.seconds) - _duration / 2
        _shape_end = attrs.peak_time.convert(UnitTypesTime.seconds) + _duration / 2

        _timestep = timestep.convert(UnitTypesTime.seconds)
        _scs_path = attrs.scs_file_path
        _scstype = attrs.scs_type

        tt = np.arange(0, _duration + 1, _timestep)

        # rainfall
        scs_df = pd.read_csv(_scs_path, index_col=0)
        scstype_df = scs_df[_scstype]
        tt_rain = _shape_start + scstype_df.index.to_numpy() * _duration
        rain_series = scstype_df.to_numpy()
        rain_instantaneous = np.diff(rain_series) / np.diff(
            tt_rain / UnitfulTime(1, UnitTypesTime.hours).convert(UnitTypesTime.seconds)
        )  # divide by time in hours to get mm/hour

        # interpolate instanetaneous rain intensity timeseries to tt
        rain_interp = np.interp(
            tt,
            tt_rain,
            np.concatenate(([0], rain_instantaneous)),
            left=0,
            right=0,
        )

        rainfall = (
            rain_interp
            * attrs.cumulative.value
            / np.trapz(
                rain_interp,
                tt / UnitfulTime(1, UnitTypesTime.hours).convert(UnitTypesTime.seconds),
            )
        )
        return rainfall


class GaussianTimeseriesCalculator(ITimeseriesCalculationStrategy):
    def calculate(
        self, attrs: SyntheticTimeseriesModel, timestep: UnitfulTime
    ) -> np.ndarray:
        tt = pd.date_range(
            start=REFERENCE_TIME,
            end=(REFERENCE_TIME + attrs.duration.to_timedelta()),
            freq=timestep.to_timedelta(),
        )
        tt_seconds = (tt - REFERENCE_TIME).total_seconds()

        mean = ((attrs.start_time + attrs.end_time) / 2).to_timedelta().total_seconds()
        sigma = ((attrs.end_time - attrs.start_time) / 6).to_timedelta().total_seconds()

        # 99.7% of the rain will fall within a duration of 6 sigma
        ts = attrs.peak_value.value * np.exp(-0.5 * ((tt_seconds - mean) / sigma) ** 2)
        return ts


class ConstantTimeseriesCalculator(ITimeseriesCalculationStrategy):
    def calculate(
        self, attrs: SyntheticTimeseriesModel, timestep: UnitfulTime
    ) -> np.ndarray:
        tt = pd.date_range(
            start=REFERENCE_TIME,
            end=(REFERENCE_TIME + attrs.duration.to_timedelta()),
            freq=timestep.to_timedelta(),
        )
        ts = np.where(
            (tt >= REFERENCE_TIME)
            & (tt <= (REFERENCE_TIME + attrs.duration.to_timedelta())),
            attrs.peak_value.value,
            0,
        )
        return ts


class TriangleTimeseriesCalculator(ITimeseriesCalculationStrategy):
    def calculate(
        self,
        attrs: SyntheticTimeseriesModel,
        timestep: UnitfulTime,
    ) -> np.ndarray:
        tt = pd.date_range(
            start=REFERENCE_TIME,
            end=(REFERENCE_TIME + attrs.duration.to_timedelta()),
            freq=timestep.to_timedelta(),
        )
        tt_seconds = (tt - REFERENCE_TIME).total_seconds()

        ascending_slope = (
            attrs.peak_value.value
            / (attrs.peak_time - attrs.start_time).to_timedelta().total_seconds()
        )
        descending_slope = (
            -attrs.peak_value.value
            / (attrs.end_time - attrs.peak_time).to_timedelta().total_seconds()
        )
        peak_time = attrs.peak_time.to_timedelta().total_seconds()
        start_time = attrs.start_time.to_timedelta().total_seconds()

        ts = np.piecewise(
            tt_seconds,
            [tt_seconds < peak_time, tt_seconds >= peak_time],
            [
                lambda x: np.maximum(ascending_slope * (x - start_time), 0),
                lambda x: np.maximum(
                    descending_slope * (x - peak_time) + attrs.peak_value.value, 0
                ),
                0,
            ],
        )
        return ts


class HarmonicTimeseriesCalculator(ITimeseriesCalculationStrategy):
    def calculate(
        self,
        attrs: SyntheticTimeseriesModel,
        timestep: UnitfulTime,
    ) -> np.ndarray:
        tt = pd.date_range(
            start=REFERENCE_TIME,
            end=(REFERENCE_TIME + attrs.duration.to_timedelta() * MAX_TIDAL_CYCLES),
            freq=timestep.to_timedelta(),
        )
        tt_seconds = (tt - REFERENCE_TIME).total_seconds()

        omega = 2 * math.pi / attrs.duration.convert(UnitTypesTime.seconds)
        phase_shift = attrs.peak_time.convert(UnitTypesTime.seconds)
        one_period_ts = attrs.peak_value.value * np.cos(
            omega * (tt_seconds - phase_shift)
        )

        # Repeat ts to cover the entire duration
        continuous_ts = np.tile(one_period_ts, MAX_TIDAL_CYCLES)[: len(tt_seconds)]
        return continuous_ts


### TIMESERIES ###
class SyntheticTimeseries(ITimeseries):
    CALCULATION_STRATEGIES: dict[ShapeType, ITimeseriesCalculationStrategy] = {
        ShapeType.gaussian: GaussianTimeseriesCalculator(),
        ShapeType.scs: ScsTimeseriesCalculator(),
        ShapeType.constant: ConstantTimeseriesCalculator(),
        ShapeType.triangle: TriangleTimeseriesCalculator(),
        ShapeType.harmonic: HarmonicTimeseriesCalculator(),
    }
    attrs: SyntheticTimeseriesModel

    def calculate_data(self, time_step: UnitfulTime = DEFAULT_TIMESTEP) -> np.ndarray:
        """Calculate the timeseries data using the timestep provided."""
        strategy = SyntheticTimeseries.CALCULATION_STRATEGIES.get(self.attrs.shape_type)
        if strategy is None:
            raise ValueError(f"Unsupported shape type: {self.attrs.shape_type}")
        return strategy.calculate(self.attrs, time_step)

    def to_dataframe(
        self,
        start_time: datetime | str,
        end_time: datetime | str,
        time_step: UnitfulTime = DEFAULT_TIMESTEP,
    ) -> pd.DataFrame:
        return super().to_dataframe(
            start_time=start_time,
            end_time=end_time,
            time_step=time_step,
            ts_start_time=self.attrs.start_time,
            ts_end_time=self.attrs.end_time,
        )

    @staticmethod
    def load_file(filepath: str | os.PathLike):
        """Create timeseries from toml file."""
        obj = SyntheticTimeseries()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = SyntheticTimeseriesModel.model_validate(toml)
        return obj

    def save(self, filepath: str | os.PathLike):
        """
        Save Synthetic Timeseries toml.

        Parameters
        ----------
        file : Path
            path to the location where file will be saved
        """
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.model_dump(exclude_none=True), f)

    @staticmethod
    def load_dict(data: dict[str, Any]):
        """Create timeseries from object, e.g. when initialized from GUI."""
        obj = SyntheticTimeseries()
        obj.attrs = SyntheticTimeseriesModel.model_validate(data)
        return obj


class CSVTimeseries(ITimeseries):
    attrs: CSVTimeseriesModel

    @classmethod
    def load_file(cls, path: str | Path):
        obj = cls()
        obj.attrs = CSVTimeseriesModel.model_validate({"path": path})
        return obj

    @staticmethod
    def read_csv(csvpath: str | Path) -> pd.DataFrame:
        """Read a timeseries file and return a pd.Dataframe.

        Parameters
        ----------
        csvpath : Union[str, os.PathLike]
            path to csv file that has the first column as time and the second column as waterlevel.
            time should be formatted as DEFAULT_DATETIME_FORMAT (= "%Y-%m-%d %H:%M:%S")
            Waterlevel is relative to the global datum.

        Returns
        -------
        pd.DataFrame
            Dataframe with time as index and waterlevel as first column.
        """
        df = pd.read_csv(csvpath, index_col=0, parse_dates=True)
        df.index.names = ["time"]
        return df

    def to_dataframe(
        self,
        start_time: datetime | str,
        end_time: datetime | str,
        time_step: UnitfulTime,
    ) -> pd.DataFrame:
        if isinstance(start_time, str):
            start_time = datetime.strptime(start_time, DEFAULT_DATETIME_FORMAT)
        if isinstance(end_time, str):
            end_time = datetime.strptime(end_time, DEFAULT_DATETIME_FORMAT)

        return super().to_dataframe(
            start_time=start_time,
            end_time=end_time,
            time_step=time_step,
            ts_start_time=UnitfulTime(0, UnitTypesTime.seconds),
            ts_end_time=UnitfulTime(
                (end_time - start_time).total_seconds(), UnitTypesTime.seconds
            ),
        )

    def calculate_data(
        self,
        time_step: UnitfulTime = DEFAULT_TIMESTEP,
    ) -> np.ndarray:
        """Interpolate the timeseries data using the timestep provided."""
        ts = self.read_csv(self.attrs.path)

        time_range = pd.date_range(
            start=ts.index.min(), end=ts.index.max(), freq=time_step.to_timedelta()
        )
        interpolated_df = ts.reindex(time_range).interpolate(method="linear")
        return interpolated_df.to_numpy()
