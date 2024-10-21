import csv
import glob
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import numpy as np
import pandas as pd
import tomli
import xarray as xr
from cht_meteo.meteo import (
    MeteoGrid,
    MeteoSource,
)
from pyproj import CRS
from scipy.interpolate import interp1d

from flood_adapt.object_model.interface.events import (
    EventModel,
    IEvent,
    Mode,
    Template,
)
from flood_adapt.object_model.interface.site import Site


class Event(IEvent):
    """Base class for all event types."""

    attrs: EventModel

    @staticmethod
    def get_template(filepath: Path):
        """Create Synthetic from toml file."""
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        template = Template(toml.get("template"))
        return template

    @staticmethod
    def get_mode(filepath: Path) -> Mode:
        """Get mode of the event (single or risk) from toml file."""
        with open(filepath, mode="rb") as fp:
            event_data = tomli.load(fp)
        mode = Mode(event_data.get("mode"))
        return mode

    @staticmethod
    def timeseries_shape(
        shape_type: str, duration: float, peak: float, **kwargs
    ) -> np.ndarray:
        """Create generic function to create shape timeseries for rainfall and discharge.

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
        else:
            ts = None
        return ts

    @staticmethod
    def read_csv(csvpath: Union[str, Path]) -> pd.DataFrame:
        """Read a timeseries file and return a pd.DataFrame.

        Parameters
        ----------
        csvpath : Union[str, os.PathLike]
            Path to the CSV file.

        Returns
        -------
        pd.DataFrame
            Dataframe with time as index and waterlevel as the first column.
        """
        num_columns = None
        has_header = None

        with open(csvpath, "r") as f:
            try:
                # read the first 1024 bytes to determine if there is a header
                has_header = csv.Sniffer().has_header(f.read(1024))
            except csv.Error:
                # The file is empty
                has_header = False

            f.seek(0)
            reader = csv.reader(f, delimiter=",")
            num_columns = len(next(reader)) - 1  # subtract 1 for the index column

        if has_header is None:
            raise ValueError(
                f"Could not determine if the CSV file has a header: {csvpath}."
            )
        if num_columns is None:
            raise ValueError(
                f"Could not determine the number of columns in the CSV file: {csvpath}."
            )

        df = pd.read_csv(
            csvpath,
            index_col=0,
            names=[i + 1 for i in range(num_columns)],
            header=0 if has_header else None,
            parse_dates=True,
            infer_datetime_format=True,
        )
        df.index.names = ["time"]
        return df

    def download_meteo(self, site: Site, path: Path):
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

    def add_dis_ts(
        self,
        event_dir: Path,
        site_river: list,
        input_river_df_list: Optional[list[pd.DataFrame]] = [],
    ):
        """Create pd.Dataframe timeseries for river discharge.

        Returns
        -------
        self

        """
        # Create empty list for results
        list_df = [None] * len(site_river)

        tstart = datetime.strptime(self.attrs.time.start_time, "%Y%m%d %H%M%S")
        tstop = datetime.strptime(self.attrs.time.end_time, "%Y%m%d %H%M%S")
        duration = (tstop - tstart).total_seconds()
        time_vec = pd.date_range(tstart, periods=duration / 600 + 1, freq="600S")

        for ii in range(len(site_river)):
            # generating time series of constant discharge
            if self.attrs.river[ii].source == "constant":
                dis = [self.attrs.river[ii].constant_discharge.value] * len(time_vec)
                df = pd.DataFrame.from_dict({"time": time_vec, ii + 1: dis})
                df = df.set_index("time")
                list_df[ii] = df
            # generating time series for river with shape discharge
            elif self.attrs.river[ii].source == "shape":
                # subtract base discharge from peak
                peak = (
                    self.attrs.river[ii].shape_peak.value
                    - self.attrs.river[ii].base_discharge.value
                )
                if self.attrs.river[ii].shape_type == "gaussian":
                    shape_duration = 3600 * self.attrs.river[ii].shape_duration
                    time_shift = (
                        self.attrs.time.duration_before_t0
                        + self.attrs.river[ii].shape_peak_time
                    ) * 3600
                    river = self.timeseries_shape(
                        "gaussian",
                        duration,
                        peak,
                        shape_duration=shape_duration,
                        time_shift=time_shift,
                    )
                elif self.attrs.river[ii].shape_type == "block":
                    start_shape = 3600 * (
                        self.attrs.time.duration_before_t0
                        + self.attrs.river[ii].shape_start_time
                    )
                    end_shape = 3600 * (
                        self.attrs.time.duration_before_t0
                        + self.attrs.river[ii].shape_end_time
                    )
                    river = self.timeseries_shape(
                        "block",
                        duration,
                        peak,
                        start_shape=start_shape,
                        end_shape=end_shape,
                    )
                # add base discharge to timeseries
                river += self.attrs.river[ii].base_discharge.value
                # save to object with pandas daterange
                df = pd.DataFrame.from_dict({"time": time_vec, ii + 1: river})
                df = df.set_index("time")
                df = df.round(decimals=2)
                list_df[ii] = df
            # generating time series for river with csv file
            elif self.attrs.river[ii].source == "timeseries":
                if input_river_df_list:
                    # when this is used for plotting and the event has not been saved yet there is no csv file,
                    # use list of dataframes instead (as for plotting other timeseries)
                    df_from_csv = input_river_df_list[ii]
                else:
                    # Read csv file of discharge
                    df_from_csv = Event.read_csv(
                        csvpath=event_dir.joinpath(self.attrs.river[ii].timeseries_file)
                    )
                # Interpolate on time_vec
                t0 = pd.to_datetime(time_vec[0])
                t_old = (
                    pd.to_datetime(df_from_csv.index) - pd.to_datetime(t0)
                ).total_seconds()
                t_new = (pd.to_datetime(time_vec) - pd.to_datetime(t0)).total_seconds()
                f = interp1d(t_old, df_from_csv[1].values)
                dis_new = f(t_new)
                # Create df again
                df = pd.DataFrame.from_dict({"time": time_vec, ii + 1: dis_new})
                df = df.set_index("time")
                df = df.round(decimals=2)
                # Add to list of pd.Dataframes
                list_df[ii] = df

        # Concatenate dataframes and add to event class
        if len(list_df) > 0:
            df_concat = pd.concat(list_df, axis=1)
            self.dis_df = df_concat
        else:
            self.dis_df = None
        return self

    def add_rainfall_ts(self, **kwargs):
        """Add timeseries to event for constant or shape-type rainfall, note all relative times and durations are converted to seconds.

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
        if self.attrs.rainfall.source == "constant":
            mag = self.attrs.rainfall.constant_intensity.value * np.array([1, 1])
            df = pd.DataFrame.from_dict({"time": time_vec[[0, -1]], "intensity": mag})
            df = df.set_index("time")
            self.rain_ts = df
            return self
        elif self.attrs.rainfall.source == "shape":
            cumulative = self.attrs.rainfall.cumulative.value
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
            elif self.attrs.rainfall.shape_type == "scs":
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

    def add_wind_ts(self):
        """Add constant wind or timeseries from file to event object.

        Returns
        -------
        self
            updated object with wind timeseries added in pd.DataFrame format
        """
        # generating time series of constant wind
        if self.attrs.wind.source == "constant":
            tstart = datetime.strptime(self.attrs.time.start_time, "%Y%m%d %H%M%S")
            tstop = datetime.strptime(self.attrs.time.end_time, "%Y%m%d %H%M%S")
            duration = (tstop - tstart).total_seconds()
            vmag = self.attrs.wind.constant_speed.value * np.array([1, 1])
            vdir = self.attrs.wind.constant_direction.value * np.array([1, 1])
            time_vec = pd.date_range(tstart, periods=duration / 600 + 1, freq="600S")
            df = pd.DataFrame.from_dict(
                {"time": time_vec[[0, -1]], "vmag": vmag, "vdir": vdir}
            )
            df = df.set_index("time")
            self.wind_ts = df
            return self

    # @staticmethod
    # def read_timeseries_csv(csvpath: Union[str, os.PathLike]) -> pd.DataFrame:
    #     """Read a rainfall or discharge, which have a datetime and one value column  timeseries file and return a pd.Dataframe. #TODO: make one for wind, which has two value columns

    #     Parameters
    #     ----------
    #     csvpath : Union[str, os.PathLike]
    #         path to csv file

    #     Returns
    #     -------
    #     pd.DataFrame
    #         Dataframe with time as index and waterlevel, rainfall, discharge or wind as first column.
    #     """
    #     df = pd.read_csv(csvpath, index_col=0, names=[1])
    #     df.index.names = ["time"]
    #     df.index = pd.to_datetime(df.index)
    #     return df

    def __eq__(self, other):
        if not isinstance(other, Event):
            # don't attempt to compare against unrelated types
            return NotImplemented
        attrs_1, attrs_2 = self.attrs.copy(), other.attrs.copy()
        attrs_1.__delattr__("name"), attrs_2.__delattr__("name")
        attrs_1.__delattr__("description"), attrs_2.__delattr__("description")
        return attrs_1 == attrs_2
