import glob
from datetime import datetime
from pathlib import Path

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
    def get_mode(filepath: Path) -> str:
        """get mode of the event (single or risk) from toml file"""

        with open(filepath, mode="rb") as fp:
            event_data = tomli.load(fp)
        mode = event_data["mode"]
        return mode

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
        # generating time series of constant wind
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

    def add_wind_ts(self):
        """adds wind it timeseries to event object

        Returns
        -------
        self
            updated object with wind timeseries added in pf.DataFrame format
        """
        # generating time series of constant wind
        if self.attrs.wind.source == "constant":
            df = Event.generate_wind_ts(self.attrs.time, self.attrs.wind)
            self.wind_ts = df
            return self

    def __eq__(self, other):
        if not isinstance(other, Event):
            # don't attempt to compare against unrelated types
            return NotImplemented
        attrs_1, attrs_2 = self.attrs.copy(), other.attrs.copy()
        attrs_1.__delattr__("name"), attrs_2.__delattr__("name")
        attrs_1.__delattr__("long_name"), attrs_2.__delattr__("long_name")
        return attrs_1 == attrs_2
