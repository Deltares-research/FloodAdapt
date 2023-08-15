import glob
import os
from datetime import datetime
from pathlib import Path
from typing import Union

import hydromt.raster  # noqa: F401
import numpy as np
import pandas as pd
import tomli
import xarray as xr
from cht_meteo.meteo import (
    MeteoGrid,
    MeteoSource,
)
from pyproj import CRS

from flood_adapt.object_model.interface.events import (
    EventModel,
    Mode,
    RiverModel,
    TimeModel,
    WindModel,
)
from flood_adapt.object_model.interface.site import ISite


class Event:
    """abstract parent class for all event types"""

    attrs: EventModel

    @staticmethod
    def generate_timeseries():
        ...

    @staticmethod
    def get_template(filepath: Path):
        """create Synthetic from toml file"""

        obj = Event()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = EventModel.parse_obj(toml)
        return obj.attrs.template

    @staticmethod
    def get_mode(filepath: Path) -> Mode:
        """get mode of the event (single or risk) from toml file"""

        with open(filepath, mode="rb") as fp:
            event_data = tomli.load(fp)
        mode = event_data["mode"]
        return mode

    @staticmethod
    def timeseries_shape(
        shape_type: str, duration: float, peak: float, **kwargs
    ) -> np.ndarray:
        """create generic function to create shape timeseries for rainfall and discharge

        Parameters
        ----------
        shape_type : str
            type of the shape: accepted types are gaussian, block or triangle
        duration : float
            total duration (in seconds) of the event
        peak : float
            shape_peak value

        Optional Parameters (depending on shape type)
        -------------------
        time_shift : float
            time (in seconds) between start of event and peak of the shape (only for gaussian and triangle)
        start_shape : float
            time (in seconds) between start of event and start of shape (only for triangle and block)
        end_shape : float
            time (in seconds) between start of event and end of shape (only for triangle and block)
        shape_duration : float
            duration (in seconds) of the shape (only for gaussian)

        Returns
        -------
        np.ndarray
            timeseries of the shape, corresponding to a time_vec with dt=600 seconds
        """
        time_shift = kwargs.get("time_shift", None)
        start_shape = kwargs.get("start_shape", None)
        end_shape = kwargs.get("end_shape", None)
        shape_duration = kwargs.get("shape_duration", None)
        tt = np.arange(0, duration + 1, 600)
        if shape_type == "gaussian":
            ts = peak * np.exp(-(((tt - time_shift) / (0.25 * shape_duration)) ** 2))
        elif shape_type == "block":
            ts = np.where((tt >= start_shape), peak, 0)
            ts = np.where((tt >= end_shape), 0, ts)
        elif shape_type == "triangle":
            tt_interp = [
                start_shape,
                time_shift,
                end_shape,
            ]
            value_interp = [0, peak, 0]
            ts = np.interp(tt, tt_interp, value_interp, left=0, right=0)
        return ts

    @staticmethod
    def generate_dis_ts(time: TimeModel, river: RiverModel) -> pd.DataFrame:
        # generating time series of constant river flow
        # TODO: handle multiple rivers (add as additional columns in dataframe)
        tstart = datetime.strptime(time.start_time, "%Y%m%d %H%M%S")
        tstop = datetime.strptime(time.end_time, "%Y%m%d %H%M%S")
        duration = (tstop - tstart).total_seconds()
        if river.source == "constant":
            dis = river.constant_discharge.convert("m3/s") * np.array([1, 1])
            time_vec = pd.date_range(tstart, periods=duration / 600 + 1, freq="600S")
            df = pd.DataFrame.from_dict({"time": time_vec[[0, -1]], 1: dis})
            df = df.set_index("time")
            return df
        elif river.source == "timeseries":
            raise NotImplementedError
        elif river.source == "shape":
            raise NotImplementedError
        else:
            raise ValueError(
                "A time series can only be generated for river sources " "constant",
                " or " "timeseries or shape if Synthetic" ".",
            )

    @staticmethod
    def generate_wind_ts(time: TimeModel, wind: WindModel) -> pd.DataFrame:
        tstart = datetime.strptime(time.start_time, "%Y%m%d %H%M%S")
        tstop = datetime.strptime(time.end_time, "%Y%m%d %H%M%S")
        duration = (tstop - tstart).total_seconds()
        if wind.source == "constant":
            vmag = wind.constant_speed.convert("m/s") * np.array([1, 1])
            vdir = wind.constant_direction.value * np.array([1, 1])
            time_vec = pd.date_range(tstart, periods=duration / 600 + 1, freq="600S")
            df = pd.DataFrame.from_dict(
                {"time": time_vec[[0, -1]], "vmag": vmag, "vdir": vdir}
            )
            df = df.set_index("time")
            return df
        elif wind.source == "timeseries":
            raise NotImplementedError
        else:
            raise ValueError(
                "A time series can only be generated for wind sources "
                "constant"
                " or "
                "timeseries"
                "."
            )

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
        df = pd.read_csv(csvpath, index_col=0, names=[1])
        df.index.names = ["time"]
        df.index = pd.to_datetime(df.index)
        return df

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
        t0 = datetime.strptime(self.attrs.time.start_time, "%Y%m%d %H%M%S")
        t1 = datetime.strptime(self.attrs.time.end_time, "%Y%m%d %H%M%S")
        time_range = [t0, t1]

        gfs_conus.download(time_range)

        # Create an empty list to hold the datasets
        datasets = []

        # Loop over each file and create a new dataset with a time coordinate
        for filename in sorted(glob.glob(str(path.joinpath("*.nc")))):
            # Open the file as an xarray dataset
            ds = xr.open_dataset(filename)

            # Extract the timestring from the filename and convert to pandas datetime format
            time_str = filename.split(".")[-2]
            time = pd.to_datetime(time_str, format="%Y%m%d_%H%M")

            # Add the time coordinate to the dataset
            ds["time"] = time

            # Append the dataset to the list
            datasets.append(ds)

        # Concatenate the datasets along the new time coordinate
        ds = xr.concat(datasets, dim="time")
        ds.raster.set_crs(4326)

        return ds

    def add_dis_ts(self):
        """adds discharge timeseries to event object

        Returns
        -------
        self
            updated object with wind timeseries added in pf.DataFrame format
        """
        # generating time series of constant discahrge
        # TODO: add for loop to handle multiple rivers
        if self.attrs.river.source == "constant":
            df = Event.generate_dis_ts(self.attrs.time, self.attrs.river)
            self.dis_ts = df
            return self
        elif self.attrs.river.source == "shape":
            duration = (
                self.attrs.time.duration_before_t0 + self.attrs.time.duration_after_t0
            ) * 3600
            time_shift = (
                self.attrs.time.duration_before_t0 + self.attrs.river.shape_peak_time
            ) * 3600
            start_shape = (
                self.attrs.time.duration_before_t0
                + self.attrs.river.shape_peak_time
                + self.attrs.river.shape_start_time
            ) * 3600
            end_shape = (
                self.attrs.time.duration_before_t0
                + self.attrs.river.shape_peak_time
                + self.attrs.river.shape_end_time
            ) * 3600
            # subtract base discharge from peak
            river = self.timeseries_shape(
                self.attrs.river.shape_type,
                duration,
                self.attrs.river.shape_peak.convert("m3/s")
                - self.attrs.river.base_discharge.convert("m3/s"),
                time_shift=time_shift,
                start_shape=start_shape,
                end_shape=end_shape,
            )
            # add base discharge to timeseries
            river += self.attrs.river.base_discharge.convert("m3/s")
            # save to object with pandas daterange
            time = pd.date_range(
                self.attrs.time.start_time, periods=duration / 600 + 1, freq="600S"
            )
            df = pd.DataFrame.from_dict({"time": time, 1: river})
            df = df.set_index("time")
            self.dis_ts = df
            return self

    def add_rainfall_ts(self, **kwargs):
        """add timeseries to event for constant or shape-type rainfall, note all relative times and durations are converted to seconds

        Returns
        -------
        self
            updated object with rainfall timeseries added in pd.DataFrame format
        """
        scsfile = kwargs.get("scsfile", None)
        scstype = kwargs.get("scstype", None)
        tstart = datetime.strptime(self.attrs.time.start_time, "%Y%m%d %H%M%S")
        tstop = datetime.strptime(self.attrs.time.end_time, "%Y%m%d %H%M%S")
        duration = (tstop - tstart).total_seconds()
        time_vec = pd.date_range(tstart, periods=duration / 600 + 1, freq="600S")
        # TODO: add rainfall increase from event pop-up (to be added there)
        if self.attrs.rainfall.source == "constant":
            mag = self.attrs.rainfall.constant_intensity.convert("mm/hr") * np.array(
                [1, 1]
            )
            df = pd.DataFrame.from_dict({"time": time_vec[[0, -1]], "intensity": mag})
            df = df.set_index("time")
            self.rain_ts = df
            return self
        elif self.attrs.rainfall.source == "shape":
            cumulative = self.attrs.rainfall.cumulative.convert("millimeters")
            if self.attrs.rainfall.shape_type == "gaussian":
                shape_duration = 3600 * self.attrs.rainfall.shape_duration
                peak = 8124.3 * cumulative / shape_duration
                time_shift = (
                    self.attrs.time.duration_before_t0
                    + self.attrs.rainfall.shape_peak_time
                ) * 3600
                rainfall = self.timeseries_shape(
                    "gaussian",
                    duration,
                    peak,
                    shape_duration=shape_duration,
                    time_shift=time_shift,
                )
            elif self.attrs.rainfall.shape_type == "block":
                start_shape = 3600 * (
                    self.attrs.time.duration_before_t0
                    + self.attrs.rainfall.shape_start_time
                )
                end_shape = 3600 * (
                    self.attrs.time.duration_before_t0
                    + self.attrs.rainfall.shape_end_time
                )
                shape_duration = end_shape - start_shape
                peak = 3600 * cumulative / shape_duration  # intensity in mm/hr
                rainfall = self.timeseries_shape(
                    "block",
                    duration,
                    peak,
                    start_shape=start_shape,
                    end_shape=end_shape,
                )
            elif self.attrs.rainfall.shape_type == "triangle":
                start_shape = 3600 * (
                    self.attrs.time.duration_before_t0
                    + self.attrs.rainfall.shape_start_time
                )
                end_shape = 3600 * (
                    self.attrs.time.duration_before_t0
                    + self.attrs.rainfall.shape_end_time
                )
                time_shift = (
                    self.attrs.time.duration_before_t0
                    + self.attrs.rainfall.shape_peak_time
                ) * 3600
                shape_duration = end_shape - start_shape
                peak = 2 * 3600 * cumulative / shape_duration
                rainfall = self.timeseries_shape(
                    "triangle",
                    duration,
                    peak,
                    start_shape=start_shape,
                    end_shape=end_shape,
                    time_shift=time_shift,
                )
            elif (
                self.attrs.rainfall.shape_type == "scs"
            ):  # TODO once we have the non-dimensional timeseries of SCS rainfall curves
                start_shape = 3600 * (
                    self.attrs.time.duration_before_t0
                    + self.attrs.rainfall.shape_start_time
                )
                shape_duration = 3600 * self.attrs.rainfall.shape_duration
                tt = np.arange(0, duration + 1, 600)

                # rainfall
                scs_df = pd.read_csv(scsfile, index_col=0)
                scstype_df = scs_df[scstype]
                tt_rain = start_shape + scstype_df.index.to_numpy() * shape_duration
                rain_series = scstype_df.to_numpy()
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
                rainfall = rain_interp * cumulative / np.trapz(rain_interp, tt / 3600)

            df = pd.DataFrame.from_dict(
                {"time": time_vec, "intensity": rainfall.round(decimals=2)}
            )
            df = df.set_index("time")
            self.rain_ts = df
            return self
        elif self.attrs.rainfall.source == "timeseries":
            df = self.read_timeseries_csv(self.attrs.rainfall.rainfall_timeseries_file)
            self.rain_ts = df
            return self

    def add_wind_ts(self):
        """adds wind it timeseries to event object

        Returns
        -------
        self
            updated object with wind timeseries added in pd.DataFrame format
        """
        # generating time series of constant wind
        if self.attrs.wind.source == "constant":
            df = Event.generate_wind_ts(self.attrs.time, self.attrs.wind)
            self.wind_ts = df
            return self

    @staticmethod
    def read_timeseries_csv(csvpath: Union[str, os.PathLike]) -> pd.DataFrame:
        """Read a rainfall or discharge, which have a datetime and one value column  timeseries file and return a pd.Dataframe. #TODO: make one for wind, which has two value columns

        Parameters
        ----------
        csvpath : Union[str, os.PathLike]
            path to csv file

        Returns
        -------
        pd.DataFrame
            Dataframe with time as index and waterlevel as first column.
        """
        df = pd.read_csv(csvpath, index_col=0, names=[1])
        df.index.names = ["time"]
        df.index = pd.to_datetime(df.index)
        return df

    def __eq__(self, other):
        if not isinstance(other, Event):
            # don't attempt to compare against unrelated types
            return NotImplemented
        attrs_1, attrs_2 = self.attrs.copy(), other.attrs.copy()
        attrs_1.__delattr__("name"), attrs_2.__delattr__("name")
        attrs_1.__delattr__("long_name"), attrs_2.__delattr__("long_name")
        return attrs_1 == attrs_2
