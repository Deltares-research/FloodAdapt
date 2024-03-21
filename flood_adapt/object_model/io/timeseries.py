import os
from abc import ABC, abstractmethod
from typing import Any, Protocol, Union

import numpy as np
import tomli
import tomli_w

from flood_adapt.object_model.interface.events import ShapeType, TimeseriesModel
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulIntensity,
    UnitfulTime,
    UnitTypesIntensity,
    UnitTypesTime,
)


class ITimeseriesCalculationStrategy(Protocol):
    @abstractmethod
    def calculate(self, attrs: TimeseriesModel) -> np.ndarray: ...


class ScsTimeseriesCalculator(ITimeseriesCalculationStrategy):
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
        ts = np.piecewise(
            tt,
            [
                tt < _shape_start,
                (tt >= _shape_start) & (tt <= _shape_end),
                tt > _shape_end,
            ],
            [0, _peak_intensity, 0],
        )
        return ts


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


class BlockTimeseriesCalculator(ITimeseriesCalculationStrategy):
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


class FileTimeseriesCalculator(ITimeseriesCalculationStrategy):
    def calculate(
        self,
        attrs: TimeseriesModel,
        timestep: UnitfulTime,
    ) -> np.ndarray:
        # TODO: implement file reading + interpolating to get the timeseries
        raise NotImplementedError


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


class Timeseries(ITimeseries):
    def __init__(self):
        self.calculation_strategies = {
            ShapeType.gaussian: GaussianTimeseriesCalculator(),
            ShapeType.scs: ScsTimeseriesCalculator(),
            ShapeType.block: BlockTimeseriesCalculator(),
            ShapeType.triangle: TriangleTimeseriesCalculator(),
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

    def load_dict(data: dict[str, Any]):
        """create timeseries from object, e.g. when initialized from GUI"""
        obj = Timeseries()
        obj.attrs = TimeseriesModel.model_validate(data)
        return obj

    # def plot(
    #     self, time_unit: UnitTypesTime, intensity_unit: UnitTypesIntensity
    # ) -> None:
    #     _start_time = self.attrs.start_time.convert(UnitTypesTime.seconds)
    #     _end_time = self.attrs.end_time.convert(UnitTypesTime.seconds)

    #     time_vector = np.arange((_end_time - _start_time).value)
    #     time_conversion = UnitfulTime(1, UnitTypesTime.seconds).convert(time_unit)

    #     _time_vector = time_vector * time_conversion.value

    #     intensity_conversion = (
    #         UnitfulIntensity(1, self.attrs.peak_intensity.units)
    #         .convert(intensity_unit)
    #         .value
    #     )
    #     _timeseries = self.data * intensity_conversion

    #     # Plot the event time vector with the overlayed timeseries
    #     plt.plot(_time_vector, _timeseries)
    #     plt.xlabel(f"Time ({time_unit.name})")
    #     plt.ylabel(f"Intensity ({intensity_unit.name})")
    #     plt.title(f"Event Timeseries Plot for shape: {self.attrs.shape_type}")
    #     plt.grid(True)
    #     plt.show()


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

    def plot(self) -> None:
        import matplotlib.pyplot as plt

        _start_time = self.start_time.convert(UnitTypesTime.seconds)
        _end_time = self.end_time.convert(UnitTypesTime.seconds)

        time_vector = np.arange((_end_time - _start_time).value)

        time_conversion = UnitfulTime(1, UnitTypesTime.seconds).convert(self.time_unit)
        intensity_conversion = UnitfulIntensity(1, UnitTypesIntensity.mm_hr).convert(
            self.intensity_unit
        )

        _time_vector = time_vector * time_conversion.value
        _timeseries = self.data * intensity_conversion.value

        # Plot the event time vector with the overlayed timeseries
        plt.plot(_time_vector, _timeseries)
        plt.xlabel(f"Time ({self.time_unit.name})")
        plt.ylabel(f"Intensity ({self.intensity_unit.name})")
        plt.title("Event Timeseries Plot")
        plt.grid(True)
        plt.show()
