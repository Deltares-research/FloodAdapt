import glob
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

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
from scipy.interpolate import interp1d

from flood_adapt.object_model.interface.events import (
    Constants,
    Defaults,
    EventModel,
    IEvent,
    Mode,
    RainfallSource,
    RiverSource,
    ShapeType,
    Template,
    WindSource,
)
from flood_adapt.object_model.interface.site import ISite


class Event(IEvent):
    """
    Base event class for all event types that contains the common attributes and methods for all events.
    This class should not be used directly, but only through its subclasses.
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
        obj.attrs = EventModel.parse_obj(toml)
        return obj

    @staticmethod
    def load_dict(data: dict[str, Any]):
        """create Projection from object, e.g. when initialized from GUI"""
        obj = Event()
        obj.attrs = EventModel.parse_obj(data)
        return obj

    @staticmethod
    def get_template(filepath: Path) -> Template:
        """get template of the event (synthetic, historical or hurricane) from toml file"""
        obj = Event()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = EventModel.parse_obj(toml)
        template = obj.attrs.template

        if not isinstance(template, Template):
            raise ValueError(f"Unsupported template: {template}.")
        return template

    @staticmethod
    def get_mode(filepath: Path) -> Mode:
        """get mode of the event (single or risk) from toml file"""

        with open(filepath, mode="rb") as fp:
            event_data = tomli.load(fp)
        mode = event_data["mode"]
        if not isinstance(mode, Mode):
            raise ValueError(f"Unsupported mode: {mode}.")
        return mode

    @staticmethod
    def create_timeseries_from_shape(
        shape_type: ShapeType,
        shape_start: float,
        shape_end: float,
        peak_height: float,
        time_step: float = Defaults._TIMESTEP,
    ) -> np.ndarray:
        """Create timeseries for different rainfall or discharge shapes.

        Parameters
        ----------
        shape_type : ShapeType
            Type of the shape: accepted types are ShapeType.GAUSSIAN, ShapeType.BLOCK, or ShapeType.TRIANGLE.
        shape_start : float
            Start time (in seconds) of the shape.
        shape_end : float
            End time (in seconds) of the shape.
        peak_height : float
            Height of the peak of the shape.
        time_step : float, optional
            Time step (in seconds) of the returned timeseries. By default 600.

        Returns
        -------
        np.ndarray
            Timeseries of the shape, corresponding to a time vector with dt=time_step seconds.
        """
        tt = np.arange(
            0, shape_end + 1, time_step
        )  # Adjust if needed to fit your specific time frame

        if shape_type == ShapeType.GAUSSIAN:
            mean = (shape_start + shape_end) / 2
            sigma = (
                shape_end - shape_start
            ) / 6  # 99.7% of the rain will fall within a duration of 6 sigma
            ts = peak_height * np.exp(-0.5 * ((tt - mean) / sigma) ** 2)

        elif shape_type == ShapeType.BLOCK:
            ts = np.where((tt >= shape_start) & (tt <= shape_end), peak_height, 0)

        elif shape_type == ShapeType.TRIANGLE:
            slope_up = peak_height / ((shape_end - shape_start) / 2)
            slope_down = -peak_height / ((shape_end - shape_start) / 2)
            peak_time = (shape_start + shape_end) / 2
            ts = np.piecewise(
                tt,
                [tt < peak_time, tt >= peak_time],
                [
                    lambda x: slope_up * (x - shape_start),
                    lambda x: slope_down * (x - shape_end) + peak_height,
                    0,
                ],
            )
        else:
            raise ValueError(f"Unsupported shape type: {shape_type}.")

        return ts

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
        t0 = datetime.strptime(self.attrs.time.start_time, Defaults._DATETIME_FORMAT)
        t1 = datetime.strptime(self.attrs.time.end_time, Defaults._DATETIME_FORMAT)
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
            time = pd.to_datetime(
                time_str, format=Defaults._DATETIME_FORMAT.replace(" ", "_")
            )

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
        time_step: float = Defaults._TIMESTEP,
        input_river_df_list: Optional[list[pd.DataFrame]] = [],
    ):
        """Creates pd.Dataframe timeseries for river discharge

        Returns
        -------
        self

        """

        # Create empty list for results
        list_df = [None] * len(site_river)

        tstart = datetime.strptime(
            self.attrs.time.start_time, Defaults._DATETIME_FORMAT
        )
        tstop = datetime.strptime(self.attrs.time.end_time, Defaults._DATETIME_FORMAT)
        duration = (tstop - tstart).total_seconds()
        time_vec = pd.date_range(
            tstart, periods=(duration / (time_step + 1)), freq=f"{time_step}S"
        )

        for ii in range(len(site_river)):
            # generating time series of constant discharge
            if self.attrs.river[ii].source == RiverSource.CONSTANT:
                dis = [self.attrs.river[ii].constant_discharge.value] * len(time_vec)
                df = pd.DataFrame.from_dict({"time": time_vec, ii + 1: dis})
                df = df.set_index("time")
                list_df[ii] = df

            # generating time series for river with shape discharge
            elif self.attrs.river[ii].source == RiverSource.SHAPE:

                shape_start = (
                    self.attrs.time.duration_before_t0
                    + self.attrs.river[ii].shape_start_time
                ) * Constants._SECONDS_PER_HOUR
                shape_end = (
                    self.attrs.time.duration_after_t0
                    + self.attrs.river[ii].shape_end_time
                ) * Constants._SECONDS_PER_HOUR

                # subtract base discharge from peak
                peak_height = (
                    self.attrs.river[ii].shape_peak.value
                    - self.attrs.river[ii].base_discharge.value
                )

                river = self.create_timeseries_from_shape(
                    shape_type=self.attrs.river[ii].shape_type,
                    shape_start=shape_start,
                    shape_end=shape_end,
                    peak_height=peak_height,
                )

                # add base discharge to timeseries
                river += self.attrs.river[ii].base_discharge.value
                # save to object with pandas daterange
                df = pd.DataFrame.from_dict({"time": time_vec, ii + 1: river})
                df = df.set_index("time")
                df = df.round(decimals=2)
                list_df[ii] = df

            # generating time series for river with csv file
            elif self.attrs.river[ii].source == RiverSource.TIMESERIES:
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

    def add_rainfall_ts(
        self, time_step: float = Defaults._TIMESTEP, scsfile=None, scstype=None
    ):
        """
        Add timeseries to event for constant or shape-type rainfall.

        Parameters
        ----------
        time_step : float, optional
            Time step of the generated rainfall time series, by default 600 seconds
        scsfile : str, optional
            Path to the SCS rainfall file, required if `source` is set to 'shape', by default None
        scstype : str, optional
            SCS rainfall type, required if `source` is set to 'shape', by default None

        Returns
        -------
        self
            Updated Event object with rainfall timeseries added in pd.DataFrame format
        """
        tstart = datetime.strptime(
            self.attrs.time.start_time, Defaults._DATETIME_FORMAT
        )
        tstop = datetime.strptime(self.attrs.time.end_time, Defaults._DATETIME_FORMAT)
        duration = (tstop - tstart).total_seconds()
        time_vec = pd.date_range(
            tstart, periods=duration / time_step + 1, freq=f"{time_step}S"
        )

        if self.attrs.rainfall.source == RainfallSource.CONSTANT:
            mag = self.attrs.rainfall.constant_intensity.value * np.array([1, 1])
            df = pd.DataFrame.from_dict({"time": time_vec[[0, -1]], "intensity": mag})

        elif self.attrs.rainfall.source == RainfallSource.SHAPE:

            shape_start = Constants._SECONDS_PER_HOUR * (
                self.attrs.time.duration_before_t0
                + self.attrs.rainfall.shape_start_time
            )
            shape_end = Constants._SECONDS_PER_HOUR * (
                self.attrs.time.duration_before_t0 + self.attrs.rainfall.shape_end_time
            )

            rainfall = self.create_rainfall_shape_ts(
                shape_type=self.attrs.rainfall.shape_type,
                shape_start=shape_start,
                shape_end=shape_end,
                time_step=time_step,
                scsfile=scsfile,
                scstype=scstype,
            )
            # TODO make time_vec & rainfaill same size & align them based on shape_start and shape_end vs tstart & tstop
            df = pd.DataFrame.from_dict(
                {"time": time_vec, "intensity": rainfall.round(decimals=2)}
            )

        else:
            raise ValueError(
                f"Unsupported rainfall source: {self.attrs.rainfall.source}."
            )

        df = df.set_index("time")
        self.rain_ts = df
        return self

    def create_rainfall_shape_ts(
        self,
        shape_start: float,
        shape_end: float,
        time_step: float,
        scsfile: Optional[str] = None,
        scstype: Optional[str] = None,
    ) -> np.ndarray:
        """Create timeseries for different rainfall shapes.

        Parameters
        ----------
        time_step : float
            Time step (in seconds) of the returned timeseries
        scsfile : [str, None]
            Path to SCS rainfall shape file
        scstype : [str, None]
            Type of SCS rainfall shape

        Returns
        -------
        np.ndarray
            Timeseries of the shape, corresponding to a time vector with dt=time_step seconds.
        """
        # Default values
        shape_duration = shape_end - shape_start
        cumulative = self.attrs.rainfall.cumulative.value
        peak_height = (
            2 * Constants._SECONDS_PER_HOUR * cumulative / shape_duration
        )  # Where does the number 2 come from?

        # Overwrite peak height for gaussian shape
        if self.attrs.rainfall.shape_type == ShapeType.GAUSSIAN:
            peak_height = (
                8124.3 * cumulative / shape_duration
            )  # Where does the number 8124.3 come from?

        # SCS is completely custom
        elif self.attrs.rainfall.shape_type == ShapeType.SCS:
            if scsfile is None or scstype is None:
                raise ValueError(
                    f"scsfile and scstype must be provided for SCS rainfall shape: {scsfile}, {scstype}"
                )
            tt = np.arange(0, shape_duration + 1, time_step)

            # rainfall
            scs_df = pd.read_csv(scsfile, index_col=0)
            scstype_df = scs_df[scstype]
            tt_rain = shape_start + scstype_df.index.to_numpy() * shape_duration
            rain_series = scstype_df.to_numpy()
            rain_instantaneous = np.diff(rain_series) / np.diff(
                tt_rain / Constants._SECONDS_PER_HOUR
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
                * cumulative
                / np.trapz(rain_interp, tt / Constants._SECONDS_PER_HOUR)
            )
            return rainfall

        # Default behavior for all shapes except SCS
        rainfall = self.create_timeseries_from_shape(
            self.attrs.rainfall.shape_type,
            shape_start=shape_start,
            shape_end=shape_end,
            peak_height=peak_height,
        )
        return rainfall

    def add_wind_ts(self, time_step: float = Defaults._TIMESTEP):
        """Adds constant wind or timeseries from file to event object.

        Parameters
        ----------
        time_step : float, optional
            Time step for generating the time series of constant wind, by default 600 seconds

        Returns
        -------
        self
            Updated object with wind timeseries added in pd.DataFrame format
        """
        # generating time series of constant wind
        if self.attrs.wind.source == WindSource.CONSTANT:
            tstart = datetime.strptime(
                self.attrs.time.start_time, Defaults._DATETIME_FORMAT
            )
            tstop = datetime.strptime(
                self.attrs.time.end_time, Defaults._DATETIME_FORMAT
            )
            duration = (tstop - tstart).total_seconds()
            vmag = self.attrs.wind.constant_speed.value * np.array([1, 1])
            vdir = self.attrs.wind.constant_direction.value * np.array([1, 1])
            time_vec = pd.date_range(
                tstart, periods=duration / time_step + 1, freq=f"{time_step}S"
            )
            df = pd.DataFrame.from_dict(
                {"time": time_vec[[0, -1]], "vmag": vmag, "vdir": vdir}
            )
            df = df.set_index("time")
            self.wind_ts = df
        else:
            raise ValueError(f"Unsupported wind source: {self.attrs.wind.source}.")
        return self

    def __eq__(self, other):
        if not isinstance(other, Event):
            # don't attempt to compare against unrelated types
            return NotImplemented
        attrs_1, attrs_2 = self.attrs.copy(), other.attrs.copy()
        attrs_1.__delattr__("name"), attrs_2.__delattr__("name")
        attrs_1.__delattr__("description"), attrs_2.__delattr__("description")
        return attrs_1 == attrs_2
