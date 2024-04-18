import os
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

import numpy as np
import pandas as pd
import tomli_w
from pydantic import BaseModel, Field, field_validator, model_validator

from flood_adapt.object_model.hazard.event.timeseries import (
    DEFAULT_DATETIME_FORMAT,
    DEFAULT_TIMESTEP,
    SyntheticTimeseries,
    TimeseriesModel,
)
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDirection,
    UnitfulDischarge,
    UnitfulLength,
    UnitfulTime,
    UnitfulVelocity,
    UnitTypesDischarge,
    UnitTypesLength,
    UnitTypesTime,
)


# Enums
class EventMode(str, Enum):
    """class describing the accepted input for the variable mode in Event"""

    single_event = "single_event"
    risk = "risk"


class WindSource(str, Enum):
    timeseries = "timeseries"
    none = "none"
    track = "track"
    map = "map"
    constant = "constant"


class WindModel(BaseModel):
    source: WindSource
    constant_speed: Optional[UnitfulVelocity] = None
    constant_direction: Optional[UnitfulDirection] = None
    timeseries_file: Optional[Union[str, Path]] = None

    @model_validator(mode="after")
    def validate_windModel(self):
        if self.source == WindSource.timeseries:
            if self.timeseries_file is None:
                raise ValueError(
                    "Timeseries file must be set when source is timeseries"
                )
            elif Path(self.timeseries_file).suffix != ".csv":
                raise ValueError("Timeseries file must be a .csv file")
            elif not Path(self.timeseries_file).is_file():
                raise ValueError("Timeseries file must be a valid file")

        elif self.source == WindSource.constant:
            if self.constant_speed is None:
                raise ValueError("Constant speed must be set when source is constant")
            elif self.constant_direction is None:
                raise ValueError(
                    "Constant direction must be set when source is constant"
                )
        return self


class RainfallSource(str, Enum):
    none = "none"
    timeseries = "timeseries"
    file = "file"
    track = "track"
    map = "map"


class RainfallModel(BaseModel):
    source: RainfallSource
    multiplier: float = Field(default=1.0, ge=0.0)

    timeseries: Optional[TimeseriesModel] = None
    csv_file: Optional[Union[str, Path]] = None

    @model_validator(mode="after")
    def validate_rainfallModel(self):
        if self.source == RainfallSource.timeseries:
            if self.timeseries is None:
                raise ValueError(
                    "TimeseriesModel must be set when source is timeseries"
                )
        return self


class RiverDischargeModel(BaseModel):
    timeseries: TimeseriesModel
    base_discharge: UnitfulDischarge = UnitfulDischarge(0, UnitTypesDischarge.cms)

    @model_validator(mode="after")
    def validate_riverDischargeModel(self):
        if not isinstance(self.timeseries.peak_intensity, UnitfulDischarge):
            raise ValueError(
                "Peak intensity must be a UnitfulDischarge when describing a river discharge"
            )
        return self


class Timing(str, Enum):
    """class describing the accepted input for the variable timng in Event"""

    historical = "historical"
    idealized = "idealized"


DEFAULT_START_TIME = "2020-01-01 00:00:00"
DEFAULT_END_TIME = "2020-01-03 00:00:00"


class TimeModel(BaseModel):
    """
    BaseModel describing the start and end times of an event model.
    Used by all event types.
    In the format of a string that is parsed as a datetime object, e.g. "2020-01-01 00:00:00" (YYYY-MM-DD HH:MM:SS)
    """

    start_time: str = DEFAULT_START_TIME
    end_time: str = DEFAULT_END_TIME

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time_format(cls, value):
        try:
            datetime.strptime(value, DEFAULT_DATETIME_FORMAT)
        except ValueError:
            raise ValueError(
                f"Time must be in format {DEFAULT_DATETIME_FORMAT}. Got {value}"
            )
        return value

    @model_validator(mode="after")
    def validate_timeModel(self):
        if datetime.strptime(
            self.start_time, DEFAULT_DATETIME_FORMAT
        ) > datetime.strptime(self.end_time, DEFAULT_DATETIME_FORMAT):
            raise ValueError("Start time must be before end time")

        return self


class TideSource(str, Enum):
    timeseries = "timeseries"
    model = "model"


class TideModel(BaseModel):
    """BaseModel describing the expected variables and data types for harmonic tide parameters of synthetic model"""

    source: TideSource
    timeseries: Optional[TimeseriesModel] = None

    @model_validator(mode="after")
    def validate_tideModel(self):
        if self.source == TideSource.timeseries:
            if self.timeseries is None:
                raise ValueError(
                    "Timeseries Model must be set when source is timeseries"
                )
        return self


class SurgeSource(str, Enum):
    none = "none"
    timeseries = "timeseries"


class SurgeModel(BaseModel):
    """BaseModel describing the expected variables and data types for harmonic tide parameters of synthetic model"""

    source: SurgeSource
    timeseries: Optional[TimeseriesModel] = None

    @model_validator(mode="after")
    def validate_surgeModel(self):
        if self.source == SurgeSource.timeseries:
            if self.timeseries is None:
                raise ValueError(
                    "Timeseries Model must be set when source is timeseries"
                )
        return self


class TranslationModel(BaseModel):
    """BaseModel describing the expected variables and data types for translation parameters of hurricane model"""

    eastwest_translation: UnitfulLength = UnitfulLength(
        value=0.0, units=UnitTypesLength.meters
    )

    northsouth_translation: UnitfulLength = UnitfulLength(
        value=0.0, units=UnitTypesLength.meters
    )


class EventTemplate(str, Enum):
    Synthetic = "Synthetic"
    Hurricane = "Hurricane"
    Historical = "Historical"


class IEventModel(BaseModel):
    """BaseModel describing all variables and data types of attributes common to all event types"""

    # Required attrs & models
    name: str  # -> name of the event
    mode: EventMode  # -> single / risk
    time: TimeModel  # -> start_time, end_time as datetime objects
    template: EventTemplate  # -> Synthetic, Hurricane, Historical

    # Optional attrs & models
    description: Optional[str] = None
    wind: Optional[WindModel] = None
    river: Optional[list[RiverDischargeModel]] = None
    tide: Optional[TideModel] = None
    surge: Optional[SurgeModel] = None
    rainfall: Optional[RainfallModel] = None
    water_level_offset: Optional[UnitfulLength] = None
    # validate source in ts, constant, none
    # no validation needed, is site dependent
    # validate synth: source == ts, histrical & hurricane = model
    # validate synth: source == ts, histrical & hurricane = none
    # validate synth: source != map/track, historical: any,  & hurricane = track/map
    # validate synth: must be set, historical & hurricane = None


class SyntheticEventModel(IEventModel):
    # TODO add validators
    @field_validator("template")
    @classmethod
    def validate_syntheticEventModel_template(cls, value):
        if value != EventTemplate.Synthetic:
            raise ValueError(f"Template must be {EventTemplate.Synthetic}. Got {value}")
        return value

    @model_validator(mode="after")
    def validate_synthetic_event_model_water_level_offset(self):
        if self.water_level_offset is None:
            raise ValueError("Water level offset must be set for a synthetic event")
        return self

    @model_validator(mode="after")
    def validate_synthetic_event_model_water_levels(self):
        if self.surge.source is not None:
            if self.surge.source != SurgeSource.timeseries:
                raise ValueError(
                    f"Surge source should be a {SurgeSource.timeseries} for a synthetic event"
                )
        if self.tide is not None:
            if self.tide.source != TideSource.timeseries:
                raise ValueError(
                    f"Tide source should be {TideSource.timeseries} for a synthetic event"
                )
        return self


class HistoricalEventModel(IEventModel):
    # TODO add validators
    @field_validator("template")
    @classmethod
    def validate_syntheticEventModel_template(cls, value):
        if value != EventTemplate.Historical:
            raise ValueError(
                f"Template must be {EventTemplate.Historical}. Got {value}"
            )
        return value

    @model_validator(mode="after")
    def validate_historical_event_model_water_level_source(self):
        if self.surge is None:
            raise ValueError("Surge must be set for historical events")
        if self.tide is None:
            if self.surge.source != SurgeSource.none:
                raise ValueError(
                    f"Surge source must be {SurgeSource.none} for historical events"
                )
            if self.tide.source != TideSource.model:
                raise ValueError(
                    f"Tide source should be {TideSource.model} for historical events"
                )
        return self


class HurricaneModel(BaseModel):
    track_name: str
    hurricane_translation: TranslationModel


class HurricaneEventModel(IEventModel):
    hurricane: HurricaneModel

    @field_validator("template")
    @classmethod
    def validate_hurricaneEventModel_template(cls, value):
        if value != EventTemplate.Hurricane:
            raise ValueError(f"Template must be {EventTemplate.Hurricane}. Got {value}")
        return value


# TODO investigate
class EventSetModel(BaseModel):
    """BaseModel describing the expected variables and data types of attributes common to a risk event that describes the probabilistic event set"""

    # add WindModel etc as this is shared among all? templates
    # TODO validate
    name: str
    mode: EventMode
    description: Optional[str] = None
    subevent_name: Optional[list[str]] = None
    frequency: Optional[list[float]] = None


class IEvent(ABC):
    attrs: IEventModel

    dis_df: pd.DataFrame = None
    rainfall_ts: pd.DataFrame = None
    overland_wind_ts: pd.DataFrame = None
    offshore_wind_ts: pd.DataFrame = None
    tide_surge_ts: pd.DataFrame = None

    def save(self, filepath: Union[str, os.PathLike]) -> None:
        """Saving event toml

        Parameters
        ----------
        file : Path
            path to the location where file will be saved
        """
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.model_dump(exclude_none=True), f)

    @staticmethod
    @abstractmethod
    def load_file(self, filepath: Union[str, os.PathLike]) -> "IEvent":
        """create Event from toml file"""
        ...

    @staticmethod
    @abstractmethod
    def load_dict(data: dict[str, Any]) -> "IEvent":
        """create Event from object, e.g. when initialized from GUI"""
        ...

    def add_river_discharge_ts(
        self,
        event_dir: Path,
        site_river: list[RiverDischargeModel] = None,
        time_step: UnitfulTime = DEFAULT_TIMESTEP,
    ) -> "IEvent":
        """
        Compute timeseries of the event generated from the combination of:
        1.  Timing Model:
            determines the total duration of the event and has default values of 0 for the whole duration of the event
        2.  List of River Discharge Models:
            determines the timeframe (start & end) of the river discharge timeseries within the event, and the intensity of the discharge

        Parameters
        ----------
        event_dir : Path
            Path to the directory where the river discharge timeseries are stored
        time_step : UnitfulTime, optional
            Time step of the generated time series, by default 600 seconds

        Returns
        -------
        Self
            The river discharge timeseries is stored in the self.dis_df attribute, in pd.DataFrame format with time as index and each river discharge as a column.
        """
        if site_river is None:
            self.dis_df = None
            return self

        # Create empty list for results
        list_df = []
        event_start = datetime.strptime(
            self.attrs.time.start_time, DEFAULT_DATETIME_FORMAT
        )
        event_end = datetime.strptime(self.attrs.time.end_time, DEFAULT_DATETIME_FORMAT)

        for ii, rivermodel in enumerate(site_river):
            rivermodel = rivermodel.model_copy(deep=True)
            rivermodel.timeseries.start_time = (
                event_start + rivermodel.timeseries.start_time.to_timedelta()
            )
            rivermodel.timeseries.end_time = (
                event_start + rivermodel.timeseries.end_time.to_timedelta()
            )
            rivermodel.timeseries.peak_intensity = (
                rivermodel.timeseries.peak_intensity - rivermodel.base_discharge
            )
            # rivermodel.timeseries.csv_file_path = (
            #     event_dir / rivermodel.timeseries.csv_file_path
            # )

            discharge = SyntheticTimeseries.load_dict(
                rivermodel.timeseries
            ).to_dataframe(
                start_time=event_start, end_time=event_end, time_step=time_step
            )
            discharge += rivermodel.base_discharge.value
            list_df[ii] = discharge

            # Concatenate dataframes and add to event class
            self.dis_df = (
                pd.concat(list_df, axis=1, join="outer")
                .interpolate(method="time")  # interpolate missing values in between
                .fillna(method="ffill")  # fill missing values at the beginning
                .fillna(method="bfill")  # fill missing values at the end
            )
        return self

    def add_rainfall_ts(self, time_step: UnitfulTime = DEFAULT_TIMESTEP) -> "IEvent":
        """
        Compute timeseries of the event generated from the combination of:
        1.  Timing Model:
            determines the total duration of the event and has default values of 0 for the whole duration of the event
        2.  Timeseries model:
            determines the timeframe (start & end) of the rainfall timeseries within the event, and the intensity of the rainfall

        Parameters
        ----------
        time_step : UnitfulTime, optional
            Time step of the generated time series, by default 600 seconds

        Returns
        -------
        Self
            The rainfall timeseries is stored in the self.rainfall_ts attribute, in pd.DataFrame format with time as index and intensity as first column.
        """
        event_start = datetime.strptime(
            self.attrs.time.start_time, DEFAULT_DATETIME_FORMAT
        )
        event_end = datetime.strptime(self.attrs.time.end_time, DEFAULT_DATETIME_FORMAT)

        rainfall_model = self.attrs.overland.rainfall
        if rainfall_model.source == RainfallSource.timeseries:
            event_rainfall_df = SyntheticTimeseries.load_dict(
                rainfall_model.timeseries
            ).to_dataframe(
                start_time=event_start, end_time=event_end, time_step=time_step
            )
            self.rainfall_ts = event_rainfall_df
        elif rainfall_model.source == RainfallSource.file:
            raise NotImplementedError("Rainfall from file not yet implemented")
        else:  # track, map, none
            raise ValueError(f"Unsupported rainfall source: {rainfall_model.source}.")
        return self

    def add_overland_wind_ts(
        self, time_step: UnitfulTime = DEFAULT_TIMESTEP
    ) -> "IEvent":
        """Adds constant wind or timeseries from overlandModel to event object.

        Parameters
        ----------
        time_step : UnitfulTime, optional
            Time step for generating the time series of constant wind, by default 600 seconds

        Returns
        -------
        Self
            Updated object with wind timeseries added to self.overland_wind_ts in pd.DataFrame format with time as index,
            the magnitude of the wind speed as first column and the direction as second column.
        """
        tstart = datetime.strptime(self.attrs.time.start_time, DEFAULT_DATETIME_FORMAT)
        tstop = datetime.strptime(self.attrs.time.end_time, DEFAULT_DATETIME_FORMAT)
        duration = (tstop - tstart).total_seconds()
        time_vec = pd.date_range(
            tstart, periods=duration / time_step + 1, freq=f"{time_step}S"
        )
        if self.attrs.overland.wind.source == WindSource.constant:
            vmag = self.attrs.overland.wind.constant_speed.value * np.array([1, 1])
            vdir = self.attrs.overland.wind.constant_direction.value * np.array([1, 1])
            df = pd.DataFrame.from_dict(
                {"time": time_vec[[0, -1]], "vmag": vmag, "vdir": vdir}
            )

        elif self.attrs.overland.wind.source == WindSource.timeseries:
            wind_df = pd.read_csv(self.attrs.overland.wind.timeseries_file)
            df = pd.DataFrame.from_dict(
                {
                    "time": time_vec[[0, -1]],
                    "vmag": wind_df["vmag"],
                    "vdir": wind_df["vdir"],
                }
            )
        else:  # track, map, none
            raise ValueError(
                f"Unsupported wind source: {self.attrs.overland.wind.source}."
            )

        df = df.set_index("time")
        self.overland_wind_ts = df
        return self

    def add_offshore_wind_ts(
        self, time_step: UnitfulTime = DEFAULT_TIMESTEP
    ) -> "IEvent":
        """Adds constant wind or timeseries from offshoreModel to event object.

        Parameters
        ----------
        time_step : UnitfulTime, optional
            Time step for generating the time series of constant wind, by default 600 seconds

        Returns
        -------
        self
            Updated object with wind timeseries added to self.offshore_wind_ts in pd.DataFrame format with time as index,
            the magnitude of the wind speed as first column and the direction as second column.
        """
        tstart = datetime.strptime(self.attrs.time.start_time, DEFAULT_DATETIME_FORMAT)
        tstop = datetime.strptime(self.attrs.time.end_time, DEFAULT_DATETIME_FORMAT)
        time_step = int(time_step.convert(UnitTypesTime.seconds).value)
        time_vec = pd.date_range(start=tstart, end=tstop, freq=f"{time_step}S")

        if self.attrs.offshore.wind.source == WindSource.constant:
            vmag = self.attrs.offshore.wind.constant_speed.value * np.array([1, 1])
            vdir = self.attrs.offshore.wind.constant_direction.value * np.array([1, 1])
            df = pd.DataFrame.from_dict(
                {"time": time_vec[[0, -1]], "vmag": vmag, "vdir": vdir}
            )

        elif self.attrs.offshore.wind.source == WindSource.timeseries:
            wind_df = pd.read_csv(self.attrs.offshore.wind.timeseries_file)
            df = pd.DataFrame.from_dict(
                {
                    "time": time_vec[[0, -1]],
                    "vmag": wind_df["vmag"],
                    "vdir": wind_df["vdir"],
                }
            )
        else:  # track, map, none
            raise ValueError(
                f"Unsupported wind source: {self.attrs.offshore.wind.source}."
            )

        df = df.set_index("time")
        self.offshore_wind_ts = df
        return self

    def add_tide_and_surge_ts(
        self, time_step: UnitfulTime = DEFAULT_TIMESTEP
    ) -> "IEvent":
        """
        Compute timeseries of the event generated from the combination of:
        1.  Timing Model:
            determines the total duration of the event and has default values of 0 for the whole duration of the event
        2.  TideModel:
            determines the timeframe (start, end & phase) of the tide timeseries within the event, and the harmonic amplitude of the tide
        3.  SurgeModel:
            determines the timeframe (start & end) of the surge timeseries within the event, and the intensity of the surge

        Parameters
        ----------
        time_step : UnitfulTime, optional
            Time step of the generated time series, by default 600 seconds

        Returns
        -------
        Self
            The tide and surge timeseries is stored in the self.tide_surge_ts attribute, in pd.DataFrame format with time as index and intensity as first column.
        """
        event_start = datetime.strptime(
            self.attrs.time.start_time, DEFAULT_DATETIME_FORMAT
        )
        event_end = datetime.strptime(self.attrs.time.end_time, DEFAULT_DATETIME_FORMAT)

        surge_model = self.attrs.surge
        if surge_model is not None:
            if surge_model.source == SurgeSource.timeseries:
                event_surge_df = SyntheticTimeseries.load_dict(
                    surge_model.timeseries
                ).to_dataframe(
                    start_time=event_start, end_time=event_end, time_step=time_step
                )
            else:  # track, map, none
                raise ValueError(f"Unsupported surge source: {surge_model.source}.")

        tide_model = self.attrs.tide
        if tide_model is not None:
            if tide_model.source == TideSource.timeseries:
                tide_model.timeseries.start_time = UnitfulTime(
                    0, UnitTypesTime.seconds
                )  # tide is always oscillating
                tide_model.timeseries.end_time = UnitfulTime(
                    event_end.timestamp(), UnitTypesTime.seconds
                )
                event_tide_df = SyntheticTimeseries.load_dict(
                    tide_model.timeseries
                ).to_dataframe(
                    start_time=event_start, end_time=event_end, time_step=time_step
                )
            else:  # track, map, none
                raise ValueError(f"Unsupported tide source: {tide_model.source}.")

        # Add final tide and surge timeseries to event if specified
        if event_surge_df is None:
            self.tide_surge_ts = event_tide_df
        elif event_tide_df is None:
            self.tide_surge_ts = event_surge_df
        else:
            self.tide_surge_ts = event_surge_df.add(
                event_tide_df, axis="index", fill_value=0
            )
        return self

    def __eq__(self, other) -> bool:
        if not isinstance(other, IEvent):
            # don't attempt to compare against unrelated types
            raise NotImplementedError
        attrs_1, attrs_2 = self.attrs.model_copy(), other.attrs.model_copy()
        attrs_1.__delattr__("name"), attrs_2.__delattr__("name")
        attrs_1.__delattr__("description"), attrs_2.__delattr__("description")
        return attrs_1 == attrs_2
