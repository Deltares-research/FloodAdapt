import glob
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union

import cht_observations.observation_stations as cht_station
import hydromt.raster  # noqa: F401
import numpy as np
import pandas as pd
import tomli
import tomli_w
import xarray as xr
from cht_meteo.meteo import (
    MeteoGrid,
    MeteoSource,
)
from pyproj import CRS

from flood_adapt.object_model.interface.events import (
    DEFAULT_DATETIME_FORMAT,
    DEFAULT_TIMESTEP,
    EventModel,
    IEvent,
    Mode,
    RainfallSource,
    RiverDischargeModel,
    WindSource,
)
from flood_adapt.object_model.interface.site import ISite
from flood_adapt.object_model.io.timeseries import Timeseries
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulLength,
    UnitfulTime,
    UnitTypesLength,
)


class Event(IEvent):
    """
    Base event class for all event types that contains pydantic models that are validated containing all the attributes, and also all methods for events.
    """

    @staticmethod
    def save(self, filepath: Union[str, os.PathLike]):
        """saving event toml

        Parameters
        ----------
        file : Path
            path to the location where file will be saved
        """
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """create Projection from toml file"""
        obj = Event()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = EventModel.model_validate(toml)
        return obj

    @staticmethod
    def load_dict(data: dict[str, Any]):
        """create Projection from object, e.g. when initialized from GUI"""
        obj = Event()
        obj.attrs = EventModel.model_validate(data)
        return obj

    @staticmethod
    def get_mode(filepath: Path) -> Mode:
        """get mode of the event (single or risk) from toml file"""

        with open(filepath, mode="rb") as fp:
            event_data = tomli.load(fp)
        mode = event_data["mode"]
        if not isinstance(mode, Mode):
            raise ValueError(f"Unsupported mode: {mode}.")
        return mode

    def download_meteo(self, site: ISite, path: Path):
        params = ["wind", "barometric_pressure", "precipitation"]
        lon = site.attrs.lon
        lat = site.attrs.lat

        # Download the actual datasets
        gfs_source = MeteoSource(
            "gfs_anl_0p50", "gfs_anl_0p50_04", "hindcast", delay=None
        )

        # Create subset
        name = "gfs_anl_0p50_us_southeast"
        gfs_conus = MeteoGrid(
            name=name,
            source=gfs_source,
            parameters=params,
            path=path,
            x_range=[lon - 10, lon + 10],
            y_range=[lat - 10, lat + 10],
            crs=CRS.from_epsg(4326),
        )

        # Download and collect data
        t0 = datetime.strptime(self.attrs.time.start_time, DEFAULT_DATETIME_FORMAT)
        t1 = datetime.strptime(self.attrs.time.end_time, DEFAULT_DATETIME_FORMAT)
        time_range = [t0, t1]

        gfs_conus.download(time_range)

        datasets = []
        for filename in sorted(glob.glob(str(path.joinpath("*.nc")))):
            # Open the file as an xarray dataset
            ds = xr.open_dataset(filename)

            # Extract the timestring from the filename and convert to pandas datetime format
            time_str = filename.split(".")[-2]
            time = pd.to_datetime(
                time_str, format=DEFAULT_DATETIME_FORMAT.replace(" ", "_")
            )

            # Add the time coordinate to the dataset
            ds["time"] = time

            # Append the dataset to the list
            datasets.append(ds)

        # Concatenate the datasets along the new time coordinate
        ds = xr.concat(datasets, dim="time")
        ds.raster.set_crs(4326)

        return ds

    def add_river_discharge_ts(
        self,
        event_dir: Path,
        site_river: list[RiverDischargeModel],
        time_step: UnitfulTime = DEFAULT_TIMESTEP,
        input_river_df_list: Optional[list[pd.DataFrame]] = None,
    ):
        """Creates pd.Dataframe timeseries for river discharge and stores all created timeseries in self.dis_df.

        Returns
        -------
        self

        """

        # Create empty list for results
        list_df = []
        tstart = datetime.strptime(self.attrs.time.start_time, DEFAULT_DATETIME_FORMAT)

        for ii, rivermodel in enumerate(site_river):
            attr_dict = {
                "shape_type": rivermodel.timeseries.shape_type,
                "shape_start": (
                    tstart + rivermodel.timeseries.start_time.to_timedelta()
                ).total_seconds(),
                "shape_end": (
                    tstart + rivermodel.timeseries.end_time.to_timedelta()
                ).total_seconds(),
                "peak_height": (
                    rivermodel.timeseries.peak_intensity - rivermodel.base_discharge
                ).value,
                "cumulative": rivermodel.timeseries.cumulative,
                "csv_file_path": event_dir / rivermodel.timeseries.csv_file_path,
                "scstype": rivermodel.timeseries.scstype,
            }

            discharge = Timeseries.load_dict(attr_dict).to_dataframe(time_step)
            discharge += rivermodel.base_discharge.value
            list_df[ii] = discharge

        # Concatenate dataframes and add to event class
        if len(list_df) > 0:
            self.dis_df = (
                pd.concat(list_df, axis=1, join="outer")
                .interpolate(method="time")  # interpolate missing values in between
                .fillna(method="ffill")  # fill missing values at the beginning
                .fillna(method="bfill")  # fill missing values at the end
                .round(decimals=2)
            )
        else:
            self.dis_df = None
        return self

    def compute_rainfall_ts(
        self, time_step: UnitfulTime = DEFAULT_TIMESTEP
    ) -> pd.DataFrame:
        """
        Compute timeseries of the event generated from the combination of:
        1.  Timing Model:
            determines the total duration of the event and has default values of 0 for the whole duration of the event
        2.  Timeseries model:
            determines the timeframe (start & end) of the rainfall timeseries within the event, and the intensity of the rainfall


        Parameters
        ----------
        time_step : UnitfulTime, optional
            Time step of the generated rainfall time series, by default 600 seconds

        Returns
        -------
            Rainfall timeseries added in pd.DataFrame format with time as index and intensity as first column.
        """
        event_start = datetime.strptime(
            self.attrs.time.start_time, DEFAULT_DATETIME_FORMAT
        )
        event_end = datetime.strptime(self.attrs.time.end_time, DEFAULT_DATETIME_FORMAT)

        rainfall_model = self.attrs.overland.rainfall
        if rainfall_model.source == RainfallSource.timeseries:
            event_rainfall_df = Timeseries.load_dict(
                rainfall_model.timeseries
            ).to_dataframe(
                start_time=event_start, end_time=event_end, time_step=time_step
            )
        else:  # track, map, none
            raise ValueError(f"Unsupported rainfall source: {rainfall_model.source}.")

        return event_rainfall_df

    def add_overland_wind_ts(self, time_step: float = DEFAULT_TIMESTEP):
        """Adds constant wind or timeseries from overlandModel to event object.

        Parameters
        ----------
        time_step : float, optional
            Time step for generating the time series of constant wind, by default 600 seconds

        Returns
        -------
        self
            Updated object with wind timeseries added in pd.DataFrame format
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
            wind_df = Timeseries.read_csv(self.attrs.overland.wind.timeseries_file)
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

    def add_offshore_wind_ts(self, time_step: float = DEFAULT_TIMESTEP):
        """Adds constant wind or timeseries from the OffshoreModel to event object.

        Parameters
        ----------
        time_step : float, optional
            Time step for generating the time series of constant wind, by default 600 seconds

        Returns
        -------
        self
            Updated object with wind timeseries added in pd.DataFrame format
        """
        tstart = datetime.strptime(self.attrs.time.start_time, DEFAULT_DATETIME_FORMAT)
        tstop = datetime.strptime(self.attrs.time.end_time, DEFAULT_DATETIME_FORMAT)
        duration = (tstop - tstart).total_seconds()
        time_step = int(time_step)
        time_vec = pd.date_range(
            tstart, periods=duration / time_step + 1, freq=f"{time_step}S"
        )
        if self.attrs.offshore.wind.source == WindSource.constant:
            vmag = self.attrs.offshore.wind.constant_speed.value * np.array([1, 1])
            vdir = self.attrs.offshore.wind.constant_direction.value * np.array([1, 1])
            df = pd.DataFrame.from_dict(
                {"time": time_vec[[0, -1]], "vmag": vmag, "vdir": vdir}
            )

        elif self.attrs.offshore.wind.source == WindSource.timeseries:
            wind_df = Timeseries.read_csv(self.attrs.offshore.wind.timeseries_file)
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

    def __eq__(self, other):
        if not isinstance(other, Event):
            # don't attempt to compare against unrelated types
            raise NotImplementedError
        attrs_1, attrs_2 = self.attrs.model_copy(), other.attrs.model_copy()
        attrs_1.__delattr__("name"), attrs_2.__delattr__("name")
        attrs_1.__delattr__("description"), attrs_2.__delattr__("description")
        return attrs_1 == attrs_2

    @staticmethod
    def download_wl_data(
        station_id: int, start_time_str: str, stop_time_str: str, units: UnitTypesLength
    ) -> pd.DataFrame:
        """Download waterlevel data from NOAA station using station_id, start and stop time.

        Parameters
        ----------
        station_id : int
            NOAA observation station ID.
        start_time_str : str
            Start time of timeseries in the form of: "YYYMMDD HHMMSS"
        stop_time_str : str
            End time of timeseries in the form of: "YYYMMDD HHMMSS"

        Returns
        -------
        pd.DataFrame
            Dataframe with time as index and waterlevel as first column.
        """
        start_time = datetime.strptime(start_time_str, "%Y%m%d %H%M%S")
        stop_time = datetime.strptime(stop_time_str, "%Y%m%d %H%M%S")
        # Get NOAA data
        source = cht_station.source("noaa_coops")
        df = source.get_data(station_id, start_time, stop_time)
        df = pd.DataFrame(df)  # Convert series to dataframe
        df = df.rename(columns={"v": 1})
        # convert to gui units
        metric_units = UnitfulLength(value=1.0, units=UnitTypesLength.meters)
        conversion_factor = metric_units.convert(units)
        df = conversion_factor * df
        return df
