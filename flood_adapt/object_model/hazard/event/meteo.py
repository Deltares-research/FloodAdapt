from datetime import datetime
from pathlib import Path
import glob

from pyproj import CRS
import xarray as xr
import pandas as pd
from cht_meteo.meteo import (
    MeteoGrid,
    MeteoSource,
)

from flood_adapt.object_model.hazard.interface.models import TimeModel
from flood_adapt.object_model.interface.site import SiteModel

def download_meteo(
    meteo_dir: Path,
    time: TimeModel,
    site: SiteModel
):
    params = ["wind", "barometric_pressure", "precipitation"]

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
        path=meteo_dir,
        x_range=[site.lon - 10, site.lon + 10],
        y_range=[site.lat - 10, site.lat + 10],
        crs=CRS.from_epsg(4326),
    )

    # Download and collect data
    t0 = time.start_time
    t1 = time.end_time
    if not isinstance(t0, datetime):
        t0 = datetime.strptime(t0, "%Y%m%d %H%M%S")
    if not isinstance(t1, datetime):
        t1 = datetime.strptime(t1, "%Y%m%d %H%M%S")

    time_range = [t0, t1]

    gfs_conus.download(time_range)

def read_meteo(
    meteo_dir: Path,
    time: TimeModel = None,
    site: SiteModel = None
) -> xr.Dataset:
    if time is not None and site is not None:
        download_meteo(time=time, meteo_dir=meteo_dir, site=site)
    
    # Create an empty list to hold the datasets
    datasets = []
    # Loop over each file and create a new dataset with a time coordinate
    for filename in sorted(glob.glob(str(meteo_dir.joinpath("*.nc")))):
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
    ds = ds.rename({"barometric_pressure": "press"})
    ds = ds.rename({"precipitation": "precip"})

    return ds