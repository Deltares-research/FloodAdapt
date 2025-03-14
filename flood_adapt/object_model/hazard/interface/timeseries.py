from abc import ABC, abstractmethod
from datetime import timedelta
from pathlib import Path
from typing import Generic, Optional, Protocol, TypeVar

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pydantic import BaseModel, model_validator

from flood_adapt.object_model.hazard.interface.forcing import (
    Scstype,
    ShapeType,
)
from flood_adapt.object_model.hazard.interface.models import TimeModel
from flood_adapt.object_model.io import unit_system as us
from flood_adapt.object_model.io.csv import read_csv

TValueUnitPair = TypeVar("TValueUnitPair", bound=us.ValueUnitPair)


class SyntheticTimeseriesModel(BaseModel, Generic[TValueUnitPair]):
    # Required
    shape_type: ShapeType
    duration: us.UnitfulTime
    peak_time: us.UnitfulTime

    # Either one of these must be set
    peak_value: Optional[TValueUnitPair] = None
    cumulative: Optional[TValueUnitPair] = None

    # Optional
    scs_file_name: Optional[str] = None
    scs_type: Optional[Scstype] = None
    fill_value: float = 0.0

    @model_validator(mode="after")
    def validate_timeseries_model_start_end_time(self):
        if self.duration.value < 0:
            raise ValueError(
                f"Timeseries shape duration must be positive, got {self.duration}"
            )
        return self

    @model_validator(mode="after")
    def validate_timeseries_model_value_specification(self):
        if (self.peak_value is None and self.cumulative is None) or (
            self.peak_value is not None and self.cumulative is not None
        ):
            raise ValueError(
                "Either peak_value or cumulative must be specified for the timeseries model."
            )
        return self

    @model_validator(mode="after")
    def validate_attrs(self):
        match self.shape_type:
            case ShapeType.scs:
                if not all(
                    attr is not None
                    for attr in [self.scs_file_name, self.scs_type, self.cumulative]
                ):
                    raise ValueError(
                        f"SCS timeseries must have `scs_file_name`, `scs_type` and `cumulative` specified. {self.scs_file_name, self.scs_type, self.cumulative}"
                    )
            case ShapeType.gaussian:
                # Gaussian shape allows for peak_value or cumulative to be set
                pass
            case _:
                if not self.peak_value:
                    raise ValueError(
                        f"Timeseries must have `peak_value` specified. {self.peak_time, self.duration, self.cumulative}"
                    )
        return self

    @property
    def start_time(self) -> us.UnitfulTime:
        return self.peak_time - self.duration / 2

    @property
    def end_time(self) -> us.UnitfulTime:
        return self.peak_time + self.duration / 2


T_UNIT = TypeVar("T_UNIT")


class CSVTimeseriesModel(BaseModel, Generic[T_UNIT]):
    path: Path
    units: T_UNIT

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


class ITimeseriesCalculationStrategy(Protocol):
    @abstractmethod
    def calculate(
        self, attrs: SyntheticTimeseriesModel, timestep: timedelta
    ) -> np.ndarray: ...


class ITimeseries(ABC):
    attrs: BaseModel

    @abstractmethod
    def calculate_data(
        self, time_step: timedelta = TimeModel().time_step
    ) -> np.ndarray:
        """Interpolate timeseries data as a numpy array with the provided time step and time as index and intensity as column."""
        ...

    def _to_dataframe(
        self,
        time_frame: TimeModel,
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
            time_frame (TimeModel):
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

    def __repr__(self):
        return f"{self.__class__.__name__}({self.attrs})"

    def __str__(self):
        return f"{self.__class__.__name__}({self.attrs})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, ITimeseries):
            raise NotImplementedError(f"Cannot compare Timeseries to {type(other)}")

        # If the following equation is element-wise True, then allclose returns True.:
        # absolute(a - b) <= (atol + rtol * absolute(b))
        return np.allclose(
            self.calculate_data(),
            other.calculate_data(),
            rtol=1e-2,
        )
