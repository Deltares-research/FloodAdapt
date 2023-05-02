from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import tomli
from pyproj import CRS

from flood_adapt.object_model.hazard.event.cht_scripts.meteo import (
    MeteoGrid,
    MeteoSource,
)
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
    def get_mode(filepath: Path):
        """create Synthetic from toml file"""

        obj = Event()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = EventModel.parse_obj(toml)
        return obj.attrs.mode

    @staticmethod
    def generate_dis_ts(time: TimeModel, river: RiverModel) -> pd.DataFrame:
        # generating time series of constant river flow
        # TODO: handle multiple rivers (add as additional columns in dataframe)
        tstart = datetime.strptime(time.start_time, "%Y%m%d %H%M%S")
        tstop = datetime.strptime(time.end_time, "%Y%m%d %H%M%S")
        duration = (tstop - tstart).total_seconds()
        if river.source == "constant":
            dis = river.constant_discharge.convert_to_cms() * np.array([1, 1])
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
            vmag = wind.constant_speed.convert_to_mps() * np.array([1, 1])
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
        
        #Determine to dowload wind and/or rainfall data
        # if self.attrs.template == "Historical_offshore":
        #     if self.attrs.wind.source == "map" and self.attrs.rainfall.source == "map":
        #         params = ["wind","barometric_pressure","precipitation"]
        #     elif self.attrs.wind.source == "map" and self.attrs.rainfall.source != "map":
        #         params = ["wind", "barometric_pressure"]
        #     elif self.attrs.wind.source != "map" and self.attrs.rainfall.source == "map":
        #         params = ["precipitation"]
        # elif self.attrs.template == "Historical_nearshore":
        #     if self.attrs.wind.source == "map" and self.attrs.rainfall.source == "map":
        #         params = ["wind","precipitation"]
        #     elif self.attrs.wind.source == "map" and self.attrs.rainfall.source != "map":
        #         params = ["wind"]
        #     elif self.attrs.wind.source != "map" and self.attrs.rainfall.source == "map":
        #         params = ["precipitation"]         
        
        params = ["wind","barometric_pressure","precipitation"]
        lon = site.attrs.lon
        lat = site.attrs.lat  

        #Download the actual datasets
        gfs_source = MeteoSource("gfs_anl_0p50",
                                 "gfs_anl_0p50",
                                 "hindcast",
                                 delay=None)

        # Create subset
        name = "gfs_anl_0p50_us_southeast"
        gfs_conus = MeteoGrid(name=name,
                              source=gfs_source,
                              parameters=params,
                              path=path,
                              x_range=[lon - 10, lon + 10],
                              y_range=[lat - 10, lat + 10],
                              crs=CRS.from_epsg(4326))

        # Download and collect data
        t0 = datetime.strptime(self.attrs.time.start_time, "%Y%m%d %H%M%S")
        t1 = datetime.strptime(self.attrs.time.end_time, "%Y%m%d %H%M%S")
        time_range = [t0, t1]

        gfs_conus.download(time_range)
        gfs_conus.collect(time_range)

        return gfs_conus
