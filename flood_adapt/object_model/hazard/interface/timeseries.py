import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Protocol

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pydantic import BaseModel, model_validator

from flood_adapt.object_model.hazard.interface.models import (
    DEFAULT_DATETIME_FORMAT,
    DEFAULT_TIMESTEP,
    TIMESERIES_VARIABLE,
    ShapeType,
)
from flood_adapt.object_model.io.unitfulvalue import (
    IUnitFullValue,
    UnitfulTime,
    UnitTypesTime,
)


def stringify_basemodel(basemodel: BaseModel):
    result = ""
    for field in basemodel.__pydantic_fields_set__:
        if isinstance(getattr(basemodel, field), BaseModel):
            result += f"{field}: {stringify_basemodel(getattr(basemodel, field))}, "
        else:
            result += f"{field}: {getattr(basemodel, field)}, "
    return f"{basemodel.__class__.__name__}({result[:-2]})"


class ITimeseriesModel(BaseModel):
    def __str__(self):
        return stringify_basemodel(self)

    def __repr__(self) -> str:
        return self.__str__()


class SyntheticTimeseriesModel(ITimeseriesModel):
    # Required
    shape_type: ShapeType
    duration: UnitfulTime
    peak_time: UnitfulTime

    # Either one of these must be set
    peak_value: Optional[TIMESERIES_VARIABLE] = None
    cumulative: Optional[TIMESERIES_VARIABLE] = None

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

    @staticmethod
    def default(ts_var: type[IUnitFullValue]) -> "SyntheticTimeseriesModel":
        return SyntheticTimeseriesModel(
            shape_type=ShapeType.gaussian,
            duration=UnitfulTime(value=2, units=UnitTypesTime.hours),
            peak_time=UnitfulTime(value=1, units=UnitTypesTime.hours),
            peak_value=ts_var(value=1, units=ts_var.DEFAULT_UNIT),
        )

    @property
    def start_time(self) -> UnitfulTime:
        return self.peak_time - self.duration / 2

    @property
    def end_time(self) -> UnitfulTime:
        return self.peak_time + self.duration / 2


class CSVTimeseriesModel(ITimeseriesModel):
    path: str | os.PathLike
    # TODO: Add validation for csv_file_path / contents ?


class ITimeseriesCalculationStrategy(Protocol):
    @abstractmethod
    def calculate(self, attrs: SyntheticTimeseriesModel) -> np.ndarray: ...


class ITimeseries(ABC):
    attrs: ITimeseriesModel

    @abstractmethod
    def calculate_data(self, time_step: UnitfulTime = DEFAULT_TIMESTEP) -> np.ndarray:
        """Interpolate timeseries data as a numpy array with the provided time step and time as index and intensity as column."""
        ...

    def to_dataframe(
        self,
        start_time: datetime | str,
        end_time: datetime | str,
        ts_start_time: UnitfulTime,
        ts_end_time: UnitfulTime,
        time_step: UnitfulTime,
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
            time_step (UnitfulTime): The time step between data points.

        Note:
            - If start_time and end_time are strings, they should be in the format DEFAULT_DATETIME_FORMAT (= "%Y-%m-%d %H:%M:%S")

        Returns
        -------
            pd.DataFrame: A pandas DataFrame with time as the index and values as the columns.
            The data is interpolated to the time_step and values that fall outside of the timeseries data are filled with 0.
        """
        if not isinstance(start_time, datetime):
            start_time = datetime.strptime(start_time, DEFAULT_DATETIME_FORMAT)
        if not isinstance(end_time, datetime):
            end_time = datetime.strptime(end_time, DEFAULT_DATETIME_FORMAT)

        full_df_time_range = pd.date_range(
            start=start_time,
            end=end_time,
            freq=time_step.to_timedelta(),
        )

        data = self.calculate_data(time_step=time_step)

        ts_time_range = pd.date_range(
            start=(start_time + ts_start_time.to_timedelta()),
            end=(start_time + ts_end_time.to_timedelta()),
            freq=time_step.to_timedelta(),
        )
        df = pd.DataFrame(data, columns=["values"], index=ts_time_range)

        full_df = df.reindex(
            index=full_df_time_range, method="nearest", limit=1, fill_value=0
        )
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

    def __eq__(self, other: "ITimeseries") -> bool:
        if not isinstance(other, ITimeseries):
            raise NotImplementedError(f"Cannot compare Timeseries to {type(other)}")

        # If the following equation is element-wise True, then allclose returns True.:
        # absolute(a - b) <= (atol + rtol * absolute(b))
        return np.allclose(
            self.calculate_data(DEFAULT_TIMESTEP),
            other.calculate_data(DEFAULT_TIMESTEP),
            rtol=1e-2,
        )
