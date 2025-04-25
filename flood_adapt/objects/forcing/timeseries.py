import os
from datetime import timedelta
from enum import Enum
from pathlib import Path
from typing import Generic, Optional, TypeVar

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import tomli
import tomli_w
from pydantic import BaseModel, model_validator

from flood_adapt.misc.path_builder import TopLevelDir, db_path
from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.forcing.csv import read_csv
from flood_adapt.objects.forcing.time_frame import REFERENCE_TIME, TimeFrame

TValueUnitPair = TypeVar("TValueUnitPair", bound=us.ValueUnitPair)


class ShapeType(str, Enum):
    gaussian = "gaussian"
    block = "block"
    triangle = "triangle"
    scs = "scs"


class Scstype(str, Enum):
    type1 = "type_1"
    type1a = "type_1a"
    type2 = "type_2"
    type3 = "type_3"


class SyntheticTimeseries(BaseModel):
    # Required
    shape_type: ShapeType
    duration: us.UnitfulTime
    peak_time: us.UnitfulTime

    # Either one of these must be set
    peak_value: Optional[us.ValueUnitPairs] = None
    cumulative: Optional[us.ValueUnitPairs] = None

    # Optional
    fill_value: float = 0.0

    @model_validator(mode="after")
    def positive_duration(self):
        if self.duration.value < 0:
            raise ValueError(
                f"Timeseries shape duration must be positive, got {self.duration}"
            )
        return self

    @model_validator(mode="after")
    def either_value_or_cumulative(self):
        if (self.peak_value is None and self.cumulative is None) or (
            self.peak_value is not None and self.cumulative is not None
        ):
            raise ValueError(
                "Either `peak_value` or `cumulative` must be specified for Synthetic Timeseries."
            )
        return self

    @property
    def start_time(self) -> us.UnitfulTime:
        return self.peak_time - self.duration / 2

    @property
    def end_time(self) -> us.UnitfulTime:
        return self.peak_time + self.duration / 2

    def calculate_data(
        self, time_step: timedelta = TimeFrame().time_step
    ) -> np.ndarray:
        """Interpolate timeseries data as a numpy array with the provided time step and time as index and intensity as column."""
        # @abstractmethod doesnt work nicely with pydantic BaseModel, so we use this instead
        raise NotImplementedError(
            "This method should be implemented in subclasses of SyntheticTimeseries."
        )

    def to_dataframe(
        self,
        time_frame: TimeFrame,
    ) -> pd.DataFrame:
        """
        Interpolate the timeseries data using the time_step provided.

        Parameters
        ----------
        start_time : datetime | str
            Start time of the timeseries.
        end_time : datetime | str
            End time of the timeseries.
        time_step : us.UnitfulTime, optional
            Time step of the timeseries, by default TimeFrame().time_step.

        """
        return self._to_dataframe(
            time_frame=time_frame,
            ts_start_time=self.start_time,
            ts_end_time=self.end_time,
            fill_value=self.fill_value,
        )

    def _to_dataframe(
        self,
        time_frame: TimeFrame,
        ts_start_time: us.UnitfulTime,
        ts_end_time: us.UnitfulTime,
        fill_value: float = 0.0,
    ) -> pd.DataFrame:
        """
        Convert timeseries data to a pandas DataFrame that has time as the index and intensity as the column.

        The dataframe time range is from start_time to end_time with the provided time_step.
        The timeseries data is added to this range by first
            - Interpolating the data to the time_step
            - Filling the missing values with 0.

        Args:
            time_frame (TimeFrame):
                The time frame for the data.
            ts_start_time (us.UnitfulTime):
                The start time of the timeseries data relative to the time_frame start time.
            ts_end_time (us.UnitfulTime):
                The end time of the timeseries data relative to the time_frame start time.
            fill_value (float, optional):
                The fill value for missing data. Defaults to 0.0.

        Returns
        -------
            pd.DataFrame: A pandas DataFrame with time as the index and values as the columns.
            The data is interpolated to the time_step and values that fall outside of the timeseries data are filled with 0.
        """
        full_df_time_range = pd.date_range(
            start=time_frame.start_time,
            end=time_frame.end_time,
            freq=time_frame.time_step,
            name="time",
        )

        data = self.calculate_data(time_step=time_frame.time_step) + fill_value

        n_cols = data.shape[1] if len(data.shape) > 1 else 1
        ts_time_range = pd.date_range(
            start=(time_frame.start_time + ts_start_time.to_timedelta()),
            end=(time_frame.start_time + ts_end_time.to_timedelta()),
            freq=time_frame.time_step,
        )

        # If the data contains more than the requested time range (from reading a csv file)
        # Slice the data to match the expected time range
        if len(data) > len(ts_time_range):
            data = data[: len(ts_time_range)]

        df = pd.DataFrame(
            data, columns=[f"data_{i}" for i in range(n_cols)], index=ts_time_range
        )

        full_df = df.reindex(
            index=full_df_time_range,
            method="nearest",
            limit=1,
            fill_value=fill_value,
        )
        full_df = full_df.set_index(full_df_time_range)
        full_df.index = pd.to_datetime(full_df.index)
        full_df.index.name = "time"
        return full_df

    @classmethod
    def load_file(cls, file_path: Path | str | os.PathLike) -> "SyntheticTimeseries":
        """Load object from file."""
        with open(file_path, mode="rb") as fp:
            toml = tomli.load(fp)
        return cls(**toml)

    def save(self, filepath: Path):
        """
        Save Synthetic Timeseries toml.

        Parameters
        ----------
        file : Path
            path to the location where file will be saved
        """
        with open(filepath, "wb") as f:
            tomli_w.dump(self.model_dump(exclude_none=True), f)

    @staticmethod
    def plot(
        df,
        xmin: pd.Timestamp,
        xmax: pd.Timestamp,
        timeseries_variable: us.ValueUnitPair,
    ) -> go.Figure:
        fig = px.line(data_frame=df)
        fig.update_layout(
            autosize=False,
            height=100 * 2,
            width=280 * 2,
            margin={"r": 0, "l": 0, "b": 0, "t": 0},
            font={"size": 10, "color": "black", "family": "Arial"},
            title_font={"size": 10, "color": "black", "family": "Arial"},
            legend=None,
            yaxis_title_font={"size": 10, "color": "black", "family": "Arial"},
            xaxis_title_font={"size": 10, "color": "black", "family": "Arial"},
            xaxis_title={"text": "Time"},
            yaxis_title={"text": f"{timeseries_variable.units}"},
            showlegend=False,
            xaxis={"range": [xmin, xmax]},
        )
        return fig

    def __eq__(self, other) -> bool:
        if not isinstance(other, SyntheticTimeseries):
            raise NotImplementedError(f"Cannot compare Timeseries to {type(other)}")

        # If the following equation is element-wise True, then allclose returns True.:
        # absolute(a - b) <= (atol + rtol * absolute(b))
        return np.allclose(
            self.calculate_data(),
            other.calculate_data(),
            rtol=1e-2,
        )


class ScsTimeseries(SyntheticTimeseries):
    shape_type: ShapeType = ShapeType.scs

    scs_file_name: str
    scs_type: Scstype

    def calculate_data(
        self, time_step: timedelta = TimeFrame().time_step
    ) -> np.ndarray:
        _duration = self.duration.convert(us.UnitTypesTime.seconds)
        _start_time = self.start_time.convert(us.UnitTypesTime.seconds)

        scs_df = pd.read_csv(
            db_path(top_level_dir=TopLevelDir.static) / "scs" / self.scs_file_name,
            index_col=0,
        )[self.scs_type]

        tt = pd.date_range(
            start=(REFERENCE_TIME + self.start_time.to_timedelta()),
            end=(REFERENCE_TIME + self.end_time.to_timedelta()),
            freq=time_step,
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
            rain_interp * self.cumulative.value / np.trapz(rain_interp, tt / 3600)
        )

        return rainfall

    @model_validator(mode="after")
    def validate_attrs(self):
        if self.cumulative is None:
            raise ValueError(
                f"SCS timeseries must have `cumulative` specified. {self.cumulative}"
            )
        return self


class GaussianTimeseries(SyntheticTimeseries):
    shape_type: ShapeType = ShapeType.gaussian

    def calculate_data(
        self, time_step: timedelta = TimeFrame().time_step
    ) -> np.ndarray:
        _start = self.start_time.convert(us.UnitTypesTime.hours)
        _end = self.end_time.convert(us.UnitTypesTime.hours)

        tt = pd.date_range(
            start=(REFERENCE_TIME + self.start_time.to_timedelta()),
            end=(REFERENCE_TIME + self.end_time.to_timedelta()),
            freq=time_step,
        )
        tt_hours = (tt - REFERENCE_TIME).total_seconds() / 3600

        mean = (_start + _end) / 2
        sigma = (_end - _start) / 6
        gaussian_curve = np.exp(-0.5 * ((tt_hours - mean) / sigma) ** 2)

        if self.cumulative:
            # Normalize to ensure the integral sums to 1 over the time steps
            integral_approx = np.trapz(gaussian_curve, tt_hours)
            normalized_gaussian = gaussian_curve / integral_approx
            ts = self.cumulative.value * normalized_gaussian.to_numpy()
        elif self.peak_value:
            ts = self.peak_value.value * gaussian_curve
        else:
            raise ValueError("Either peak_value or cumulative must be specified.")

        return ts

    @model_validator(mode="after")
    def validate_attrs(self):
        # either peak_value or cumulative must be set, which is already checked in the parent class: `either_value_or_cumulative`
        return self


class BlockTimeseries(SyntheticTimeseries):
    shape_type: ShapeType = ShapeType.block

    def calculate_data(
        self, time_step: timedelta = TimeFrame().time_step
    ) -> np.ndarray:
        tt = pd.date_range(
            start=(REFERENCE_TIME + self.start_time.to_timedelta()),
            end=(REFERENCE_TIME + self.end_time.to_timedelta()),
            freq=time_step,
        )
        if self.peak_value:
            height_value = self.peak_value.value
        elif self.cumulative:
            area = self.cumulative.value
            base = self.duration.convert(
                us.UnitTypesTime.hours
            )  # always expect duration in hours
            height_value = area / base

        ts = np.zeros((len(tt),)) + height_value
        return ts

    @model_validator(mode="after")
    def validate_attrs(self):
        # either peak_value or cumulative must be set, which is already checked in the parent class: `either_value_or_cumulative`
        return self


class TriangleTimeseries(SyntheticTimeseries):
    shape_type: ShapeType = ShapeType.triangle

    def calculate_data(
        self, time_step: timedelta = TimeFrame().time_step
    ) -> np.ndarray:
        tt = pd.date_range(
            start=(REFERENCE_TIME + self.start_time.to_timedelta()),
            end=(REFERENCE_TIME + self.end_time.to_timedelta()),
            freq=time_step,
        )
        tt_seconds = (tt - REFERENCE_TIME).total_seconds()
        peak_time = self.peak_time.to_timedelta().total_seconds()
        start_time = self.start_time.to_timedelta().total_seconds()

        if self.peak_value:
            height_value = self.peak_value.value
        elif self.cumulative:
            area = self.cumulative.value
            base = self.duration.convert(
                us.UnitTypesTime.hours
            )  # always expect duration in hours
            height_value = (2 * area) / base

        ascending_slope = (
            height_value
            / (self.peak_time - self.start_time).to_timedelta().total_seconds()
        )
        descending_slope = (
            -height_value
            / (self.end_time - self.peak_time).to_timedelta().total_seconds()
        )

        ts = np.piecewise(
            tt_seconds,
            [tt_seconds < peak_time, tt_seconds >= peak_time],
            [
                lambda x: np.maximum(ascending_slope * (x - start_time), 0),
                lambda x: np.maximum(
                    descending_slope * (x - peak_time) + height_value, 0
                ),
                0,
            ],
        )
        return ts

    @model_validator(mode="after")
    def validate_attrs(self):
        # either peak_value or cumulative must be set, which is already checked in the parent class: `either_value_or_cumulative`
        return self


class CSVTimeseries(BaseModel, Generic[TValueUnitPair]):
    path: Path
    units: TValueUnitPair

    @model_validator(mode="after")
    def validate_csv(self):
        if not self.path.exists():
            raise ValueError(f"Path {self.path} does not exist.")
        if not self.path.is_file():
            raise ValueError(f"Path {self.path} is not a file.")
        if not self.path.suffix == ".csv":
            raise ValueError(f"Path {self.path} is not a csv file.")

        # Try loading the csv file, read_csv will raise an error if it cannot read the file
        read_csv(self.path)
        return self

    @staticmethod
    def load_file(path: str | Path, units: us.ValueUnitPair):
        return CSVTimeseries[type(units)](path=Path(path), units=units)

    def to_dataframe(
        self,
        time_frame: TimeFrame,
        fill_value: float = 0,
    ) -> pd.DataFrame:
        """
        Interpolate the timeseries data using the time_step provided.

        Parameters
        ----------
        time_frame : TimeFrame
            Time frame for the data.
        fill_value : float, optional
            Value to fill missing data with, by default 0.

        Returns
        -------
        pd.DataFrame
            Interpolated timeseries with datetime index.
        """
        file_data = read_csv(self.path)

        # Ensure requested time range is within available data
        start_time = max(time_frame.start_time, file_data.index.min())
        end_time = min(time_frame.end_time, file_data.index.max())

        df = file_data.loc[start_time:end_time]

        # Generate the complete time range
        time_range = pd.date_range(
            start=time_frame.start_time,
            end=time_frame.end_time,
            freq=time_frame.time_step,
        )

        # Reindex and fill missing values with specified fill_value
        interpolated_df = (
            df.reindex(time_range, method="nearest", limit=1)
            .interpolate(method="linear")
            .fillna(fill_value)
        )
        interpolated_df.index.name = "time"
        return interpolated_df

    def calculate_data(
        self,
        time_step: timedelta = TimeFrame().time_step,
    ) -> np.ndarray:
        return read_csv(self.path).to_numpy()

    def read_time_frame(self) -> TimeFrame:
        """
        Read the time frame from the file.

        Returns
        -------
        TimeFrame
            Time frame of the data in the file.
        """
        file_data = read_csv(self.path)
        return TimeFrame(
            start_time=file_data.index.min(),
            end_time=file_data.index.max(),
        )


class TimeseriesFactory:
    @staticmethod
    def from_args(
        shape_type: ShapeType,
        duration: us.UnitfulTime,
        peak_time: us.UnitfulTime,
        peak_value: Optional[us.ValueUnitPairs] = None,
        cumulative: Optional[us.ValueUnitPairs] = None,
        fill_value: float = 0.0,
        scs_file_name: Optional[str] = None,
        scs_type: Optional[Scstype] = None,
    ) -> SyntheticTimeseries:
        """Create a timeseries object based on the shape type."""
        match shape_type:
            case ShapeType.gaussian:
                return GaussianTimeseries(
                    duration=duration,
                    peak_time=peak_time,
                    peak_value=peak_value,
                    cumulative=cumulative,
                    fill_value=fill_value,
                )
            case ShapeType.block:
                return BlockTimeseries(
                    duration=duration,
                    peak_time=peak_time,
                    peak_value=peak_value,
                    cumulative=cumulative,
                    fill_value=fill_value,
                )
            case ShapeType.triangle:
                return TriangleTimeseries(
                    duration=duration,
                    peak_time=peak_time,
                    peak_value=peak_value,
                    cumulative=cumulative,
                    fill_value=fill_value,
                )
            case ShapeType.scs:
                if scs_file_name is None or scs_type is None:
                    from flood_adapt.dbs_classes.database import Database

                    scs_config = Database().site.sfincs.scs
                    if scs_config is None:
                        raise ValueError("SCS configuration not found in database.")
                    scs_file_name = scs_file_name or scs_config.file
                    scs_type = scs_type or scs_config.type

                return ScsTimeseries(
                    duration=duration,
                    peak_time=peak_time,
                    peak_value=peak_value,
                    cumulative=cumulative,
                    fill_value=fill_value,
                    scs_file_name=scs_file_name,
                    scs_type=scs_type,
                )
            case _:
                raise ValueError(f"Unknown shape type {shape_type}.")

    @staticmethod
    def load_file(
        file_path: Path | str | os.PathLike,
    ) -> SyntheticTimeseries:
        """Load object from file."""
        with open(file_path, mode="rb") as fp:
            toml = tomli.load(fp)
        return TimeseriesFactory.from_args(
            **toml,
        )

    @staticmethod
    def from_object(obj: SyntheticTimeseries) -> SyntheticTimeseries:
        return TimeseriesFactory.from_args(**obj.model_dump(exclude_none=True))
