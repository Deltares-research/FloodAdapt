import math
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, Union

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import tomli
import tomli_w

from flood_adapt.object_model.interface.events import (
    DEFAULT_DATETIME_FORMAT,
    ShapeType,
    TimeseriesModel,
)
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulIntensity,
    UnitfulTime,
    UnitTypesIntensity,
    UnitTypesTime,
)

TIDAL_PERIOD = UnitfulTime(12.4, UnitTypesTime.hours)


class ITimeseriesCalculationStrategy(Protocol):
    @abstractmethod
    def calculate(self, attrs: TimeseriesModel) -> np.ndarray: ...


class ScsTimeseriesCalculator(ITimeseriesCalculationStrategy):
    def calculate(self, attrs: TimeseriesModel, timestep: UnitfulTime) -> np.ndarray:
        _shape_start = attrs.start_time.convert(UnitTypesTime.seconds).value
        _shape_end = attrs.end_time.convert(UnitTypesTime.seconds).value
        _duration = _shape_end - _shape_start
        _timestep = timestep.convert(UnitTypesTime.seconds).value
        _csv_path = attrs.csv_file_path
        _scstype = attrs.scstype

        tt = np.arange(0, _duration + 1, _timestep)

        # rainfall
        scs_df = pd.read_csv(_csv_path, index_col=0)
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


class FileTimeseriesCalculator(ITimeseriesCalculationStrategy):
    def calculate(
        self,
        attrs: TimeseriesModel,
        timestep: UnitfulTime,
    ) -> np.ndarray:
        """
        Read a timeseries file and return a pd.Dataframe with the provided timestep by interpolating.
        """
        df = Timeseries.read_csv(attrs.csv_file_path)
        freq = int(timestep.convert(UnitTypesTime.seconds).value)
        time_range = pd.date_range(
            start=df.index.min(), end=df.index.max(), freq=f"{freq}S", inclusive="left"
        )
        interpolated_df = df.reindex(time_range).interpolate(method="linear")
        return interpolated_df


class ITimeseries(ABC):
    attrs: TimeseriesModel

    @property
    @abstractmethod
    def data(self) -> np.ndarray:
        """get timeseries data"""
        ...

    @abstractmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """get timeseries attributes from toml file"""
        ...

    @abstractmethod
    def load_dict(data: dict[str, Any]):
        """get timeseries attributes from an object, e.g. when initialized from GUI"""
        ...

    @abstractmethod
    def save(self, filepath: Union[str, os.PathLike]):
        """save timeseries attributes to a toml file"""
        ...

    @abstractmethod
    def to_dataframe(self) -> pd.DataFrame:
        """get timeseries data as a pandas dataframe with time as index and intensity as column"""
        ...

    @abstractmethod
    def read_csv(self, filepath: Union[str, os.PathLike]) -> pd.DataFrame:
        """read csv file and return a pandas dataframe with time as index and intensity as column"""
        ...


class Timeseries(ITimeseries):
    def __init__(self):
        self.calculation_strategies: dict[ShapeType, ITimeseriesCalculationStrategy] = {
            ShapeType.gaussian: GaussianTimeseriesCalculator(),
            ShapeType.scs: ScsTimeseriesCalculator(),
            ShapeType.constant: ConstantTimeseriesCalculator(),
            ShapeType.triangle: TriangleTimeseriesCalculator(),
            ShapeType.harmonic: HarmonicTimeseriesCalculator(),
            ShapeType.csv_file: FileTimeseriesCalculator(),
        }

    @property
    def data(
        self, time_step: UnitfulTime = UnitfulTime(1, UnitTypesTime.seconds)
    ) -> np.ndarray:
        """
        Returns the calculated data for the time series with a timestep of 1 second and an intensity unit of the TimeseriesModel

        Returns:
            np.ndarray: The calculated data for the time series.
        """
        return self.calculate_data(time_step)

    def calculate_data(self, time_step: UnitfulTime) -> np.ndarray:
        """
        Calculate the timeseries data using the timestep provided
        """
        strategy = self.calculation_strategies.get(self.attrs.shape_type)
        if strategy is None:
            raise ValueError(f"Unsupported shape type: {self.attrs.shape_type}")
        return strategy.calculate(self.attrs, time_step)

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """create timeseries from toml file"""
        obj = Timeseries()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = TimeseriesModel.model_validate(toml)
        return obj

    def save(self, filepath: Union[str, os.PathLike]):
        """saving timeseries toml

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
        obj = Timeseries()
        obj.attrs = TimeseriesModel.model_validate(data)
        return obj

    def to_dataframe(
        self,
        start_time: Union[datetime, str],
        end_time: Union[datetime, str],
        time_step: UnitfulTime,
    ) -> pd.DataFrame:
        """get timeseries data as a pandas dataframe with time as index and intensity as column"""
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
            start=(start_time + self.attrs.start_time.to_timedelta()),
            end=(start_time + self.attrs.end_time.to_timedelta()),
            inclusive="left",
            freq=f"{_time_step}S",
        )
        df = pd.DataFrame(data, columns=["intensity"], index=_time_range)

        full_df = df.reindex(full_df.index, method="nearest", limit=1, fill_value=0)
        return full_df

    @staticmethod
    def read_csv(csvpath: Union[str, Path]) -> pd.DataFrame:
        """Read a timeseries file and return a pd.Dataframe.

        Parameters
        ----------
        csvpath : Union[str, os.PathLike]
            path to csv file

        Returns
        -------
        pd.DataFrame
            Dataframe with time as index and waterlevel as first column.
        """
        df = pd.read_csv(csvpath, index_col=0, header=None)
        df.index.names = ["time"]
        df.index = pd.to_datetime(df.index)
        return df

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


class CompositeTimeseries:
    timeseries_list: list[Timeseries]
    time_unit: UnitTypesTime
    intensity_unit: UnitTypesIntensity
    data: np.ndarray

    @property
    def peak_intensity(self) -> UnitfulIntensity:
        return UnitfulIntensity(np.amax(self.data), self.intensity_unit)

    @property
    def start_time(self) -> UnitfulTime:
        return min([ts.attrs.start_time for ts in self.timeseries_list])

    @property
    def end_time(self) -> UnitfulTime:
        return max([ts.attrs.end_time for ts in self.timeseries_list])

    def __init__(
        self,
        timeseries_list: list[Timeseries],
        time_unit: UnitTypesTime,
        intensity_unit: UnitTypesIntensity,
    ) -> None:
        self.timeseries_list = timeseries_list
        self.intensity_unit = intensity_unit
        self.time_unit = time_unit
        self.data = np.zeros([])
        if len(timeseries_list) > 0:
            for ts in self.timeseries_list:
                self.add(ts)

    def add(self, ts_to_add: Timeseries) -> "CompositeTimeseries":
        if not isinstance(ts_to_add, Timeseries):
            raise TypeError(
                f"Unsupported type for addition to composite timeseries. Only Timeseries is supported: {type(ts_to_add)}"
            )

        if ts_to_add.data is None:
            raise ValueError("Timeseries has no data")

        # convert all times to seconds
        comp_start_time = self.start_time.convert(UnitTypesTime.seconds)
        comp_end_time = self.end_time.convert(UnitTypesTime.seconds)
        ts_start_time = ts_to_add.attrs.start_time.convert(UnitTypesTime.seconds)
        ts_end_time = ts_to_add.attrs.end_time.convert(UnitTypesTime.seconds)

        # find the start and end time of the composite timeseries
        start_time = min(comp_start_time, ts_start_time)
        end_time = max(comp_end_time, ts_end_time)
        new_timeseries = np.zeros(int((end_time - start_time).value))

        # convert the intensity of the timeseries to be added to the same units as the composite timeseries
        ts_to_add_conversion = (
            UnitfulIntensity(1, ts_to_add.attrs.peak_intensity.units)
            .convert(self.intensity_unit)
            .value
        )

        new_timeseries[
            int((comp_start_time - start_time).value) : int(
                (comp_end_time - start_time).value
            )
        ] += self.data

        new_timeseries[
            int((ts_start_time - start_time).value) : int(
                (ts_end_time - start_time).value
            )
        ] += (ts_to_add.data * ts_to_add_conversion)

        self.data = new_timeseries
        return self

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
        # import matplotlib.pyplot as plt

        # _start_time = self.start_time.convert(UnitTypesTime.seconds)
        # _end_time = self.end_time.convert(UnitTypesTime.seconds)

        # time_vector = np.arange((_end_time - _start_time).value)

        # time_conversion = UnitfulTime(1, UnitTypesTime.seconds).convert(self.time_unit)
        # intensity_conversion = UnitfulIntensity(1, UnitTypesIntensity.mm_hr).convert(
        #     self.intensity_unit
        # )

        # _time_vector = time_vector * time_conversion.value
        # _timeseries = self.data * intensity_conversion.value

        # # Plot the event time vector with the overlayed timeseries
        # plt.plot(_time_vector, _timeseries)
        # plt.xlabel(f"Time ({self.time_unit.name})")
        # plt.ylabel(f"Intensity ({self.intensity_unit.name})")
        # plt.title("Event Timeseries Plot")
        # plt.grid(True)
        # plt.show()
