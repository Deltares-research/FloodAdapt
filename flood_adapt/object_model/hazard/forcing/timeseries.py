import os
from datetime import timedelta
from pathlib import Path
from typing import Any, Generic, Type, TypeVar

import numpy as np
import pandas as pd
import tomli
import tomli_w

from flood_adapt.object_model.hazard.interface.forcing import (
    ShapeType,
)
from flood_adapt.object_model.hazard.interface.models import REFERENCE_TIME, TimeModel
from flood_adapt.object_model.hazard.interface.timeseries import (
    CSVTimeseriesModel,
    ITimeseries,
    ITimeseriesCalculationStrategy,
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.interface.path_builder import TopLevelDir, db_path
from flood_adapt.object_model.io import unit_system as us
from flood_adapt.object_model.io.csv import read_csv


### CALCULATION STRATEGIES ###
class ScsTimeseriesCalculator(ITimeseriesCalculationStrategy):
    def calculate(
        self, attrs: SyntheticTimeseriesModel, timestep: timedelta
    ) -> np.ndarray:
        _duration = attrs.duration.convert(us.UnitTypesTime.seconds)
        _start_time = attrs.start_time.convert(us.UnitTypesTime.seconds)

        scs_df = pd.read_csv(
            db_path(top_level_dir=TopLevelDir.static) / "scs" / attrs.scs_file_name,
            index_col=0,
        )[attrs.scs_type]

        tt = pd.date_range(
            start=(REFERENCE_TIME + attrs.start_time.to_timedelta()),
            end=(REFERENCE_TIME + attrs.end_time.to_timedelta()),
            freq=timestep,
        )
        tt = (tt - REFERENCE_TIME).total_seconds()

        tt_rain = _start_time + scs_df.index.to_numpy() * _duration
        rain_series = scs_df.to_numpy()
        rain_instantaneous = np.diff(rain_series) / np.diff(
            tt_rain / 3600
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
            rain_interp * attrs.cumulative.value / np.trapz(rain_interp, tt / 3600)
        )

        return rainfall


class GaussianTimeseriesCalculator(ITimeseriesCalculationStrategy):
    def calculate(
        self, attrs: SyntheticTimeseriesModel, timestep: timedelta
    ) -> np.ndarray:
        _start = attrs.start_time.convert(us.UnitTypesTime.seconds)
        _end = attrs.end_time.convert(us.UnitTypesTime.seconds)

        tt = pd.date_range(
            start=(REFERENCE_TIME + attrs.start_time.to_timedelta()),
            end=(REFERENCE_TIME + attrs.end_time.to_timedelta()),
            freq=timestep,
        )
        tt_seconds = (tt - REFERENCE_TIME).total_seconds()

        mean = (_start + _end) / 2
        sigma = (_end - _start) / 6

        # 99.7% of the rain will fall within a duration of 6 sigma
        ts = attrs.peak_value.value * np.exp(-0.5 * ((tt_seconds - mean) / sigma) ** 2)
        return ts


class BlockTimeseriesCalculator(ITimeseriesCalculationStrategy):
    def calculate(
        self, attrs: SyntheticTimeseriesModel, timestep: timedelta
    ) -> np.ndarray:
        tt = pd.date_range(
            start=(REFERENCE_TIME + attrs.start_time.to_timedelta()),
            end=(REFERENCE_TIME + attrs.end_time.to_timedelta()),
            freq=timestep,
        )
        ts = np.zeros((len(tt),)) + attrs.peak_value.value
        return ts


class TriangleTimeseriesCalculator(ITimeseriesCalculationStrategy):
    def calculate(
        self,
        attrs: SyntheticTimeseriesModel,
        timestep: timedelta,
    ) -> np.ndarray:
        tt = pd.date_range(
            start=(REFERENCE_TIME + attrs.start_time.to_timedelta()),
            end=(REFERENCE_TIME + attrs.end_time.to_timedelta()),
            freq=timestep,
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
        ShapeType.block: BlockTimeseriesCalculator(),
        ShapeType.triangle: TriangleTimeseriesCalculator(),
    }
    attrs: SyntheticTimeseriesModel

    def __init__(self, data: dict[str, Any] | SyntheticTimeseriesModel):
        super().__init__()
        if isinstance(data, dict):
            unit_cls = _extract_unit_class(data)
            self.attrs = SyntheticTimeseriesModel[unit_cls].model_validate(data)
        elif isinstance(data, SyntheticTimeseriesModel):
            self.attrs = data
        else:
            raise TypeError(f"Unsupported data type: {type(data)}")

    def calculate_data(
        self, time_step: timedelta = TimeModel().time_step
    ) -> np.ndarray:
        """Calculate the timeseries data using the timestep provided."""
        strategy = SyntheticTimeseries.CALCULATION_STRATEGIES.get(self.attrs.shape_type)
        if strategy is None:
            raise ValueError(f"Unsupported shape type: {self.attrs.shape_type}")
        return strategy.calculate(self.attrs, time_step)

    def to_dataframe(
        self,
        time_frame: TimeModel,
    ) -> pd.DataFrame:
        """
        Interpolate the timeseries data using the timestep provided.

        Parameters
        ----------
        start_time : datetime | str
            Start time of the timeseries.
        end_time : datetime | str
            End time of the timeseries.
        time_step : us.UnitfulTime, optional
            Time step of the timeseries, by default TimeModel().time_step.

        """
        return super()._to_dataframe(
            time_frame=time_frame,
            ts_start_time=self.attrs.start_time,
            ts_end_time=self.attrs.end_time,
            fill_value=self.attrs.fill_value,
        )

    @classmethod
    def load_file(cls, file_path: Path | str | os.PathLike) -> "SyntheticTimeseries":
        """Load object from file."""
        with open(file_path, mode="rb") as fp:
            toml = tomli.load(fp)
        return cls.load_dict(toml)

    @classmethod
    def load_dict(
        cls, data: dict[str, Any] | SyntheticTimeseriesModel
    ) -> "SyntheticTimeseries":
        """Load object from dictionary."""
        return cls(data)

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


T_UNIT = TypeVar("T_UNIT", bound=Any)


class CSVTimeseries(ITimeseries, Generic[T_UNIT]):
    attrs: CSVTimeseriesModel[T_UNIT]

    @classmethod
    def load_file(cls, path: str | Path):
        obj = cls()
        obj.attrs = CSVTimeseriesModel[T_UNIT].model_validate(
            {"path": path, "units": T_UNIT}
        )
        return obj

    def to_dataframe(
        self,
        time_frame: TimeModel,
    ) -> pd.DataFrame:
        file_data = read_csv(self.attrs.path)

        # filter by time frame
        df = file_data.loc[time_frame.start_time : time_frame.end_time]
        if df.empty:
            raise ValueError(
                f"""No data in csv file for the selected time frame.\n\nRequested time frame:\t{time_frame.start_time} to {time_frame.end_time}\nFile time frame:\t\t{file_data.index.min()} to {file_data.index.max()}\nFilepath:\t\t{self.attrs.path}"""
            )

        # interpolate and fill missing values
        time_range = pd.date_range(
            start=df.index.min(), end=df.index.max(), freq=time_frame.time_step
        )
        interpolated_df = (
            df.reindex(time_range, method="nearest", limit=1)
            .interpolate(method="linear")
            .fillna(0)
        )
        interpolated_df.index.name = "time"
        return interpolated_df

    def calculate_data(
        self,
        time_step: timedelta = TimeModel().time_step,
    ) -> np.ndarray:
        return read_csv(self.attrs.path).to_numpy()


def _extract_unit_class(data: dict[str, Any]) -> Type[us.ValueUnitPair]:
    if "peak_value" in data:
        param = "peak_value"
    elif "cumulative" in data:
        param = "cumulative"
    else:
        raise ValueError("peak_value or cumulative must be specified.")

    UNITS: dict[Type, Type] = {
        us.UnitTypesLength: us.UnitfulLength,
        us.UnitTypesTime: us.UnitfulTime,
        us.UnitTypesDischarge: us.UnitfulDischarge,
        us.UnitTypesDirection: us.UnitfulDirection,
        us.UnitTypesVelocity: us.UnitfulVelocity,
        us.UnitTypesIntensity: us.UnitfulIntensity,
        us.UnitTypesArea: us.UnitfulArea,
        us.UnitTypesVolume: us.UnitfulVolume,
    }

    str_unit = data[param]["units"]
    for unit_types_class in UNITS:
        try:
            _ = unit_types_class(str_unit)
            return UNITS[unit_types_class]
        except Exception:
            continue

    raise ValueError(f"Unsupported unit: {str_unit}")
