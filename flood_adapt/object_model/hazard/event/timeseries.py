from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import tomli
import tomli_w

import flood_adapt.object_model.io.unitfulvalue as uv
from flood_adapt.object_model.hazard.interface.models import (
    DEFAULT_DATETIME_FORMAT,
    DEFAULT_TIMESTEP,
    REFERENCE_TIME,
    ShapeType,
)
from flood_adapt.object_model.hazard.interface.timeseries import (
    CSVTimeseriesModel,
    ITimeseries,
    ITimeseriesCalculationStrategy,
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.interface.path_builder import TopLevelDir, db_path
from flood_adapt.object_model.io.csv import read_csv


### CALCULATION STRATEGIES ###
class ScsTimeseriesCalculator(ITimeseriesCalculationStrategy):
    def calculate(
        self, attrs: SyntheticTimeseriesModel, timestep: uv.UnitfulTime
    ) -> np.ndarray:
        _duration = attrs.duration.convert(uv.UnitTypesTime.seconds)
        _start_time = attrs.start_time.convert(uv.UnitTypesTime.seconds)
        _timestep = timestep.convert(uv.UnitTypesTime.seconds)
        tt = np.arange(0, _duration + 1, _timestep)

        # rainfall
        scs_path = (
            db_path(top_level_dir=TopLevelDir.static) / "scs" / attrs.scs_file_name
        )
        scs_df = pd.read_csv(scs_path, index_col=0)
        scstype_df = scs_df[attrs.scs_type]
        tt_rain = _start_time + scstype_df.index.to_numpy() * _duration
        rain_series = scstype_df.to_numpy()
        rain_instantaneous = np.diff(rain_series) / np.diff(
            tt_rain
            / uv.UnitfulTime(value=1, units=uv.UnitTypesTime.hours).convert(
                uv.UnitTypesTime.seconds
            )
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
                tt
                / uv.UnitfulTime(value=1, units=uv.UnitTypesTime.hours).convert(
                    uv.UnitTypesTime.seconds
                ),
            )
        )
        return rainfall


class GaussianTimeseriesCalculator(ITimeseriesCalculationStrategy):
    def calculate(
        self, attrs: SyntheticTimeseriesModel, timestep: uv.UnitfulTime
    ) -> np.ndarray:
        tt = pd.date_range(
            start=(REFERENCE_TIME + attrs.start_time.to_timedelta()),
            end=(REFERENCE_TIME + attrs.end_time.to_timedelta()),
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
        self, attrs: SyntheticTimeseriesModel, timestep: uv.UnitfulTime
    ) -> np.ndarray:
        tt = pd.date_range(
            start=(REFERENCE_TIME + attrs.start_time.to_timedelta()),
            end=(REFERENCE_TIME + attrs.end_time.to_timedelta()),
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
        timestep: uv.UnitfulTime,
    ) -> np.ndarray:
        tt = pd.date_range(
            start=(REFERENCE_TIME + attrs.start_time.to_timedelta()),
            end=(REFERENCE_TIME + attrs.end_time.to_timedelta()),
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


### TIMESERIES ###
class SyntheticTimeseries(ITimeseries):
    CALCULATION_STRATEGIES: dict[ShapeType, ITimeseriesCalculationStrategy] = {
        ShapeType.gaussian: GaussianTimeseriesCalculator(),
        ShapeType.scs: ScsTimeseriesCalculator(),
        ShapeType.constant: ConstantTimeseriesCalculator(),
        ShapeType.triangle: TriangleTimeseriesCalculator(),
    }
    attrs: SyntheticTimeseriesModel

    def calculate_data(
        self, time_step: uv.UnitfulTime = DEFAULT_TIMESTEP
    ) -> np.ndarray:
        """Calculate the timeseries data using the timestep provided."""
        strategy = SyntheticTimeseries.CALCULATION_STRATEGIES.get(self.attrs.shape_type)
        if strategy is None:
            raise ValueError(f"Unsupported shape type: {self.attrs.shape_type}")
        return strategy.calculate(self.attrs, time_step)

    def to_dataframe(
        self,
        start_time: datetime | str,
        end_time: datetime | str,
        time_step: uv.UnitfulTime = DEFAULT_TIMESTEP,
    ) -> pd.DataFrame:
        """
        Interpolate the timeseries data using the timestep provided.

        Parameters
        ----------
        start_time : datetime | str
            Start time of the timeseries.
        end_time : datetime | str
            End time of the timeseries.
        time_step : uv.UnitfulTime, optional
            Time step of the timeseries, by default DEFAULT_TIMESTEP.

        """
        return super().to_dataframe(
            start_time=start_time,
            end_time=end_time,
            time_step=time_step,
            ts_start_time=self.attrs.start_time,
            ts_end_time=self.attrs.end_time,
        )

    @staticmethod
    def load_file(filepath: Path):
        """Create timeseries from toml file."""
        obj = SyntheticTimeseries()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = SyntheticTimeseriesModel.model_validate(toml)
        return obj

    def save(self, filepath: Path):
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
    def load_dict(
        data: dict[str, Any] | SyntheticTimeseriesModel,
    ) -> "SyntheticTimeseries":
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

    def to_dataframe(
        self,
        start_time: datetime | str,
        end_time: datetime | str,
        time_step: uv.UnitfulTime = DEFAULT_TIMESTEP,
    ) -> pd.DataFrame:
        if isinstance(start_time, str):
            start_time = datetime.strptime(start_time, DEFAULT_DATETIME_FORMAT)
        if isinstance(end_time, str):
            end_time = datetime.strptime(end_time, DEFAULT_DATETIME_FORMAT)

        return super().to_dataframe(
            start_time=start_time,
            end_time=end_time,
            time_step=time_step,
            ts_start_time=uv.UnitfulTime(0, uv.UnitTypesTime.seconds),
            ts_end_time=uv.UnitfulTime(
                (end_time - start_time).total_seconds(), uv.UnitTypesTime.seconds
            ),
        )

    def calculate_data(
        self,
        time_step: uv.UnitfulTime = DEFAULT_TIMESTEP,
    ) -> np.ndarray:
        """Interpolate the timeseries data using the timestep provided."""
        ts = read_csv(self.attrs.path)

        time_range = pd.date_range(
            start=ts.index.min(), end=ts.index.max(), freq=time_step.to_timedelta()
        )
        interpolated_df = ts.reindex(time_range).interpolate(method="linear")

        return interpolated_df.to_numpy()