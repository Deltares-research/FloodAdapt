from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Protocol, Type, Union

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pydantic import BaseModel, Field, model_validator

from flood_adapt.object_model.hazard.interface.forcing import (
    Scstype,
    ShapeType,
)
from flood_adapt.object_model.hazard.interface.models import TimeModel
from flood_adapt.object_model.io import unit_system as us
from flood_adapt.object_model.io.csv import read_csv

TIMESERIES_VARIABLE = Union[
    us.UnitfulIntensity,
    us.UnitfulDischarge,
    us.UnitfulVelocity,
    us.UnitfulLength,
    us.UnitfulHeight,
    us.UnitfulArea,
    us.UnitfulDirection,
]


class SyntheticTimeseriesModel(BaseModel):
    # Required
    shape_type: ShapeType
    duration: us.UnitfulTime
    peak_time: us.UnitfulTime

    # Either one of these must be set
    peak_value: Optional[TIMESERIES_VARIABLE] = Field(
        default=None,
        description="Peak value of the timeseries.",
        validate_default=False,
    )
    cumulative: Optional[TIMESERIES_VARIABLE] = Field(
        default=None,
        description="Cumulative value of the timeseries.",
        validate_default=False,
    )

    # Optional
    scs_file_name: Optional[str] = None
    scs_type: Optional[Scstype] = None
    fill_value: float = Field(
        default=0.0,
        description="Value used to fill the time range that falls outside of the timeseries in the to_dataframe method.",
    )

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
    def validate_scs_timeseries(self):
        if self.shape_type == ShapeType.scs:
            if not all(
                attr is not None
                for attr in [self.scs_file_name, self.scs_type, self.cumulative]
            ):
                raise ValueError(
                    f"SCS timeseries must have scs_file_name, scs_type and cumulative specified. {self.scs_file_name, self.scs_type, self.cumulative}"
                )
        return self

    @staticmethod
    def default(ts_var: Type[TIMESERIES_VARIABLE]) -> "SyntheticTimeseriesModel":
        return SyntheticTimeseriesModel(
            shape_type=ShapeType.gaussian,
            duration=us.UnitfulTime(value=2, units=us.UnitTypesTime.hours),
            peak_time=us.UnitfulTime(value=1, units=us.UnitTypesTime.hours),
            peak_value=ts_var(value=1, units=ts_var.DEFAULT_UNIT),
        )

    @property
    def start_time(self) -> us.UnitfulTime:
        return self.peak_time - self.duration / 2

    @property
    def end_time(self) -> us.UnitfulTime:
        return self.peak_time + self.duration / 2


class CSVTimeseriesModel(BaseModel):
    path: Path

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
        start_time: datetime,
        end_time: datetime,
        ts_start_time: us.UnitfulTime,
        ts_end_time: us.UnitfulTime,
        time_step: timedelta,
        fill_value: float = 0.0,
    ) -> pd.DataFrame:
        """
        Convert timeseries data to a pandas DataFrame that has time as the index and intensity as the column.

        The dataframe time range is from start_time to end_time with the provided time_step.
        The timeseries data is added to this range by first
            - Interpolating the data to the time_step
            - Filling the missing values with 0.

        Args:
            start_time (Union[datetime, str]): The start datetime of returned timeseries.
                start_time is the first index of the dataframe
            end_time (Union[datetime, str]): The end datetime of returned timeseries.
                end_time is the last index of the dataframe (date time)
            time_step (timedelta): The time step between data points.

        Returns
        -------
            pd.DataFrame: A pandas DataFrame with time as the index and values as the columns.
            The data is interpolated to the time_step and values that fall outside of the timeseries data are filled with 0.
        """
        full_df_time_range = pd.date_range(
            start=start_time,
            end=end_time,
            freq=time_step,
            name="time",
        )

        data = self.calculate_data(time_step=time_step) + fill_value

        n_cols = data.shape[1] if len(data.shape) > 1 else 1
        ts_time_range = pd.date_range(
            start=(start_time + ts_start_time.to_timedelta()),
            end=(start_time + ts_end_time.to_timedelta()),
            freq=time_step,
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
        timeseries_variable: TIMESERIES_VARIABLE,
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
            self.calculate_data(TimeModel().time_step),
            other.calculate_data(TimeModel().time_step),
            rtol=1e-2,
        )