import math
import os
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Protocol, Union

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import tomli
import tomli_w
from pydantic import BaseModel, field_validator, model_validator

from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDischarge,
    UnitfulIntensity,
    UnitfulLength,
    UnitfulTime,
    UnitfulVolume,
    UnitTypesIntensity,
    UnitTypesTime,
)

TIDAL_PERIOD = UnitfulTime(value=12.4, unitsUnitTypesTime.hours)
# DEFAULT_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_TIMESTEP = UnitfulTime(600, UnitTypesTime.seconds)


class ShapeType(str, Enum):
    gaussian = "gaussian"
    constant = "constant"
    triangle = "triangle"
    harmonic = "harmonic"
    scs = "scs"


class Scstype(str, Enum):
    type1 = "type1"
    type1a = "type1a"
    type2 = "type2"
    type3 = "type3"


class TimeseriesModel(BaseModel):
    # Required
    shape_type: ShapeType
    start_time: UnitfulTime
    end_time: UnitfulTime

    # Either one of these must be set
    peak_intensity: Optional[
        Union[UnitfulIntensity, UnitfulDischarge, UnitfulLength]
    ] = None
    cumulative: Optional[Union[UnitfulLength, UnitfulVolume]] = None

    @model_validator(mode="after")
    def validate_timeseries_model_start_end_time(self):
        if self.start_time > self.end_time:
            raise ValueError(
                f"Timeseries start time cannot be later than its end time: {self.start_time}, {self.end_time}"
            )
        return self

    # Only required for ShapeType.scs
    scs_file_path: Optional[Union[str, Path]] = None
    scs_type: Optional[Scstype] = None

    @field_validator("scs_file_path")
    @classmethod
    def validate_file_path(cls, value):
        if value is not None:
            if Path(value).suffix != ".csv":
                raise ValueError("Timeseries scs file must be a .csv file")
            elif not Path(value).is_file():
                raise ValueError("Timeseries scs file must be a valid file")
        return value

    @model_validator(mode="after")
    def validate_timeseries_model_optional_variables(self):
        if self.shape_type == ShapeType.scs:
            if (
                self.scs_file_path is None
                or self.scs_type is None
                or self.cumulative is None
            ):
                raise ValueError(
                    f"scs_file, scs_type and cumulative must be provided for SCS timeseries: {self.scs_file_path}, {self.scs_type}, {self.cumulative}"
                )
        else:
            if self.cumulative is not None and self.peak_intensity is not None:
                raise ValueError(
                    "Exactly one of peak_intensity or cumulative must be set"
                )

            if self.cumulative is None and self.peak_intensity is None:
                raise ValueError(
                    "Exactly one of peak_intensity or cumulative must be set"
                )

        return self


class ITimeseriesCalculationStrategy(Protocol):
    @abstractmethod
    def calculate(self, attrs: TimeseriesModel) -> np.ndarray: ...


class ScsTimeseriesCalculator(ITimeseriesCalculationStrategy):
    def calculate(self, attrs: TimeseriesModel, timestep: UnitfulTime) -> np.ndarray:
        _shape_start = attrs.start_time.convert(UnitTypesTime.seconds).value
        _shape_end = attrs.end_time.convert(UnitTypesTime.seconds).value
        _duration = _shape_end - _shape_start
        _timestep = timestep.convert(UnitTypesTime.seconds).value
        _scs_path = attrs.scs_file_path
        _scstype = attrs.scs_type

        tt = np.arange(0, _duration + 1, _timestep)

        # rainfall
        scs_df = pd.read_csv(_scs_path, index_col=0)
        scstype_df = scs_df[_scstype]
        tt_rain = _shape_start + scstype_df.index.to_numpy() * _duration
        rain_series = scstype_df.to_numpy()
        rain_instantaneous = np.diff(rain_series) / np.diff(
            tt_rain
            / UnitfulTime(1, UnitTypesTime.hours).convert(UnitTypesTime.seconds).value
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
                / UnitfulTime(1, UnitTypesTime.hours)
                .convert(UnitTypesTime.seconds)
                .value,
            )
        )
        return rainfall


class GaussianTimeseriesCalculator(ITimeseriesCalculationStrategy):
    def calculate(self, attrs: TimeseriesModel, timestep: UnitfulTime) -> np.ndarray:
        _shape_start = attrs.start_time.convert(UnitTypesTime.seconds).value
        _shape_end = attrs.end_time.convert(UnitTypesTime.seconds).value
        _peak_intensity = attrs.peak_intensity.value
        _timestep = timestep.convert(UnitTypesTime.seconds).value

        tt = np.arange(
            _shape_start,
            _shape_end,
            step=_timestep,
        )
        mean = (_shape_start + _shape_end) / 2
        sigma = (_shape_end - _shape_start) / 6
        # 99.7% of the rain will fall within a duration of 6 sigma
        ts = _peak_intensity * np.exp(-0.5 * ((tt - mean) / sigma) ** 2)
        return ts


class ConstantTimeseriesCalculator(ITimeseriesCalculationStrategy):
    def calculate(self, attrs: TimeseriesModel, timestep: UnitfulTime) -> np.ndarray:
        _shape_start = attrs.start_time.convert(UnitTypesTime.seconds).value
        _shape_end = attrs.end_time.convert(UnitTypesTime.seconds).value
        _peak_intensity = attrs.peak_intensity.value
        _timestep = timestep.convert(UnitTypesTime.seconds).value

        tt = np.arange(
            _shape_start,
            _shape_end,
            step=_timestep,
        )
        ts = np.where((tt > _shape_start) & (tt < _shape_end), _peak_intensity, 0)
        return ts


class TriangleTimeseriesCalculator(ITimeseriesCalculationStrategy):
    def calculate(
        self,
        attrs: TimeseriesModel,
        timestep: UnitfulTime,
    ) -> np.ndarray:
        _shape_start = attrs.start_time.convert(UnitTypesTime.seconds).value
        _shape_end = attrs.end_time.convert(UnitTypesTime.seconds).value
        _peak_intensity = attrs.peak_intensity.value
        _timestep = timestep.convert(UnitTypesTime.seconds).value

        tt = np.arange(
            _shape_start,
            _shape_end,
            step=_timestep,
        )
        peak_time = (_shape_start + _shape_end) / 2
        ascending_slope = _peak_intensity / (peak_time - _shape_start)
        descending_slope = -_peak_intensity / (_shape_end - peak_time)

        ts = np.piecewise(
            tt,
            [tt < peak_time, tt >= peak_time],
            [
                lambda x: ascending_slope * (x - _shape_start),
                lambda x: descending_slope * (x - peak_time) + _peak_intensity,
                0,
            ],
        )
        return ts


class HarmonicTimeseriesCalculator(ITimeseriesCalculationStrategy):
    def calculate(
        self,
        attrs: TimeseriesModel,
        timestep: UnitfulTime,
    ) -> np.ndarray:
        _shape_start = attrs.start_time.convert(UnitTypesTime.seconds).value
        _shape_end = attrs.end_time.convert(UnitTypesTime.seconds).value
        _peak_intensity = attrs.peak_intensity.value
        _timestep = timestep.convert(UnitTypesTime.seconds).value

        tt = np.arange(
            start=_shape_start,
            stop=_shape_end,
            step=_timestep,
        )
        omega = 2 * math.pi / (TIDAL_PERIOD / UnitfulTime(1, UnitTypesTime.days))
        ts = _peak_intensity * np.cos(
            omega
            * tt
            / UnitfulTime(1, UnitTypesTime.days).convert(UnitTypesTime.seconds).value
        )

        return ts


class TimeseriesSource(str, Enum):
    synthetic = "synthetic"
    csv = "csv"


class ITimeseries(ABC):
    source: TimeseriesSource

    @abstractmethod
    def calculate_data(self, time_step: UnitfulTime) -> np.ndarray:
        """Interpolate timeseries data as a numpy array with the provided time step and time as index and intensity as column"""
        ...

    def to_dataframe(
        self,
        start_time: Union[datetime, str],
        end_time: Union[datetime, str],
        ts_start_time: UnitfulTime,
        ts_end_time: UnitfulTime,
        time_step: UnitfulTime,
    ) -> pd.DataFrame:
        """
        Converts timeseries data to a pandas DataFrame that has time as the index and intensity as the column.
        The dataframe time range is from start_time to end_time with the provided time_step.
        The timeseries data is added to this range by first
            - Interpolating the data to the time_step
            - Filling the missing values with 0.

        Args:
            start_time (Union[datetime, str]): The start datetime of returned timeseries.
                start_time is the first index of the dataframe
            end_time (Union[datetime, str]): The end datetime of returned timeseries.
                end_time is the last index of the dataframe (date time)
            time_step (UnitfulTime): The time step between data points.

        Note:
            - If start_time and end_time are strings, they should be in the format DEFAULT_DATETIME_FORMAT (= "%Y-%m-%d %H:%M:%S")

        Returns:
            pd.DataFrame: A pandas DataFrame with time as the index and intensity as the column.
            The data is interpolated to the time_step and values that fall outside of the timeseries data are filled with 0.
        """
        if isinstance(start_time, str):
            start_time = datetime.strptime(start_time, DEFAULT_DATETIME_FORMAT)
        if isinstance(end_time, str):
            end_time = datetime.strptime(end_time, DEFAULT_DATETIME_FORMAT)

        _time_step = int(time_step.convert(UnitTypesTime.seconds).value)

        full_df_time_range = pd.date_range(
            start=start_time, end=end_time, freq=f"{_time_step}S", inclusive="left"
        )
        full_df = pd.DataFrame(index=full_df_time_range)
        full_df.index.name = "time"

        data = self.calculate_data(time_step=time_step)
        _time_range = pd.date_range(
            start=(start_time + ts_start_time.to_timedelta()),
            end=(start_time + ts_end_time.to_timedelta()),
            inclusive="left",
            freq=f"{_time_step}S",
        )
        df = pd.DataFrame(data, columns=["intensity"], index=_time_range)

        full_df = df.reindex(full_df.index, method="nearest", limit=1, fill_value=0)
        return full_df

    @staticmethod
    def plot(
        df, xmin: pd.Timestamp, xmax: pd.Timestamp, intensity_units: UnitTypesIntensity
    ) -> go.Figure:
        fig = px.line(data_frame=df)

        # fig.update_traces(marker={"line": {"color": "#000000", "width": 2}})

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
            yaxis_title={"text": f"Rainfall intensity [{intensity_units}]"},
            showlegend=False,
            xaxis={"range": [xmin, xmax]},
            # paper_bgcolor="#3A3A3A",
            # plot_bgcolor="#131313",
        )
        return fig


class SyntheticTimeseries(ITimeseries):
    attrs: TimeseriesModel

    def __init__(self):
        self.calculation_strategies: dict[ShapeType, ITimeseriesCalculationStrategy] = {
            ShapeType.gaussian: GaussianTimeseriesCalculator(),
            ShapeType.scs: ScsTimeseriesCalculator(),
            ShapeType.constant: ConstantTimeseriesCalculator(),
            ShapeType.triangle: TriangleTimeseriesCalculator(),
            ShapeType.harmonic: HarmonicTimeseriesCalculator(),
        }

    def calculate_data(self, time_step: UnitfulTime) -> np.ndarray:
        """
        Calculate the timeseries data using the timestep provided
        """
        strategy = self.calculation_strategies.get(self.attrs.shape_type)
        if strategy is None:
            raise ValueError(f"Unsupported shape type: {self.attrs.shape_type}")
        return strategy.calculate(self.attrs, time_step)

    def to_dataframe(
        self,
        start_time: datetime | str,
        end_time: datetime | str,
        time_step: UnitfulTime,
    ) -> pd.DataFrame:
        return super().to_dataframe(
            start_time=start_time,
            end_time=end_time,
            time_step=time_step,
            ts_start_time=self.attrs.start_time,
            ts_end_time=self.attrs.end_time,
        )

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """create timeseries from toml file"""
        obj = SyntheticTimeseries()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = TimeseriesModel.model_validate(toml)
        return obj

    def save(self, filepath: Union[str, os.PathLike]):
        """
        Saving Synthetic Timeseries toml

        Parameters
        ----------
        file : Path
            path to the location where file will be saved
        """
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.model_dump(exclude_none=True), f)

    @staticmethod
    def load_dict(data: dict[str, Any]):
        """create timeseries from object, e.g. when initialized from GUI"""
        obj = SyntheticTimeseries()
        obj.attrs = TimeseriesModel.model_validate(data)
        return obj

    def __eq__(self, other: "SyntheticTimeseries") -> bool:
        if not isinstance(other, SyntheticTimeseries):
            raise NotImplementedError(
                f"Cannot compare SyntheticTimeseries to {type(other)}"
            )
        return self.attrs == other.attrs


class CSVTimeseries(ITimeseries):
    csv_file_path: Union[str, Path]

    @staticmethod
    def read_csv(csvpath: Union[str, Path]) -> pd.DataFrame:
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
        df = pd.read_csv(csvpath, index_col=0, header=None)
        df.index.names = ["time"]
        df.index = pd.to_datetime(df.index, format=DEFAULT_DATETIME_FORMAT)
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
        time_step: UnitfulTime,
    ) -> np.ndarray:
        """
        Interpolate the timeseries data using the timestep provided
        """
        ts = self.read_csv(self.csv_file_path)
        freq = int(time_step.convert(UnitTypesTime.seconds).value)
        time_range = pd.date_range(
            start=ts.index.min(), end=ts.index.max(), freq=f"{freq}S", inclusive="left"
        )
        interpolated_df = ts.reindex(time_range).interpolate(method="linear")
        return interpolated_df.to_numpy()
