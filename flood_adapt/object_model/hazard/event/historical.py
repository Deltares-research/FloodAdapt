import glob
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Union

import cht_observations.observation_stations as cht_station
import hydromt.raster  # noqa: F401
import pandas as pd
import tomli
import xarray as xr
from cht_meteo.meteo import (
    MeteoGrid,
    MeteoSource,
)
from pyproj import CRS

from flood_adapt.object_model.interface.events import (
    DEFAULT_DATETIME_FORMAT,
    HistoricalEventModel,
    IEvent,
)
from flood_adapt.object_model.interface.site import ISite
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulLength,
    UnitTypesLength,
)


class HistoricalEvent(IEvent):
    """
    Event class that describes a historical/historic-based event.
    From the timing and location of the event, it can use historical gauge data & meteorological data to describe:
      Water levels
      Wind
      Barometric pressure
      Rainfall

    While still allowing to use synthetic data to overwrite or fill in missing data.
    """

    attrs: HistoricalEventModel

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]) -> "HistoricalEvent":
        """create HistoricalEvent from toml file"""
        obj = HistoricalEvent()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = HistoricalEventModel.model_validate(toml)

    @staticmethod
    def load_dict(data: dict[str, Any]) -> "HistoricalEvent":
        """create HistoricalEvent from object, e.g. when initialized from GUI"""
        obj = HistoricalEvent()
        obj.attrs = HistoricalEventModel.model_validate(data)
        return obj

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
        conversion_factor = (
            UnitfulLength(1.0, UnitTypesLength.meters).convert(units).value
        )
        df = conversion_factor * df
        return df

    @staticmethod
    def download_meteo(event: IEvent, site: ISite, path: Path):
        logging.info("Downloading meteo data...")
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
        t0 = datetime.strptime(event.attrs.time.start_time, DEFAULT_DATETIME_FORMAT)
        t1 = datetime.strptime(event.attrs.time.end_time, DEFAULT_DATETIME_FORMAT)
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
