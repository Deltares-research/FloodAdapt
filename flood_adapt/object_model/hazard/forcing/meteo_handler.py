import glob
from datetime import datetime
from pathlib import Path
from typing import Optional

import cht_meteo.cht.meteo as meteo
import numpy as np
import pandas as pd
import xarray as xr
from cht_meteo.meteo import (
    MeteoGrid,
)

from flood_adapt.misc.config import Settings
from flood_adapt.object_model.hazard.interface.meteo_handler import IMeteoHandler
from flood_adapt.object_model.hazard.interface.models import TimeModel
from flood_adapt.object_model.interface.config.site import Site


class MeteoHandler(IMeteoHandler):
    def __init__(self, dir: Optional[Path] = None, site: Optional[Site] = None) -> None:
        self.dir: Path = dir or Settings().database_path / "static" / "meteo"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.site: Site = site or Site.load_file(
            Settings().database_path / "static" / "config" / "site.toml"
        )

    def download(self, time: TimeModel):
        # Create GFS dataset
        gfs_conus = meteo.dataset(
            name="gfs_anl_0p50",
            source="gfs_analysis_0p50",
            path=self.dir,
            lon_range=(self.site.attrs.lon - 10, self.site.attrs.lon + 10),
            lat_range=(self.site.attrs.lat - 10, self.site.attrs.lat + 10),
        )

        # quick fix for sites near the 0 degree longitude -> shift the meteo download area either east or west of the 0 degree longitude
        # TODO implement a good solution to this in cht_meteo
        def _shift_grid_to_positive_lon(grid: MeteoGrid):
            """Shift the grid to positive longitudes if the grid crosses the 0 degree longitude."""
            if np.prod(grid.lon_range) < 0:
                if np.abs(grid.lon_range[0]) > np.abs(grid.lon_range[1]):
                    grid.lon_range = [
                        grid.lon_range[0] - grid.lon_range[1] - 1,
                        grid.lon_range[1] - grid.lon_range[1] - 1,
                    ]
                else:
                    grid.lon_range = [
                        grid.lon_range[0] - grid.lon_range[0] + 1,
                        grid.lon_range[1] - grid.lon_range[0] + 1,
                    ]
            return grid.lon_range

        gfs_conus.lon_range = _shift_grid_to_positive_lon(gfs_conus)

        # Download and collect data
        t0 = time.start_time
        t1 = time.end_time
        if not isinstance(t0, datetime):
            t0 = datetime.strptime(t0, "%Y%m%d %H%M%S")
        if not isinstance(t1, datetime):
            t1 = datetime.strptime(t1, "%Y%m%d %H%M%S")

        time_range = (t0, t1)

        gfs_conus.download(time_range=time_range)

    def read(self, time: TimeModel) -> xr.Dataset:
        self.download(time)

        # Create an empty list to hold the datasets
        datasets = []
        nc_files = sorted(glob.glob(str(self.dir.joinpath("*.nc"))))

        if not nc_files:
            raise FileNotFoundError(
                f"No meteo files found in meteo directory {self.dir}"
            )

        # Loop over each file and create a new dataset with a time coordinate
        for filename in nc_files:
            # Open the file as an xarray dataset
            with xr.open_dataset(filename) as ds:
                # Extract the timestring from the filename and convert to pandas datetime format
                time_str = filename.split(".")[-2]
                _time = pd.to_datetime(time_str, format="%Y%m%d_%H%M")

                # Add the time coordinate to the dataset
                ds["time"] = _time

                # Append the dataset to the list
                datasets.append(ds)

        # Concatenate the datasets along the new time coordinate
        ds = xr.concat(datasets, dim="time")
        ds.raster.set_crs(4326)

        # Rename the variables to match what hydromt-sfincs expects
        ds = ds.rename(
            {
                "barometric_pressure": "press_msl",
                "precipitation": "precip",
                "wind_u": "wind10_u",
                "wind_v": "wind10_v",
            }
        )

        # Convert the longitude to -180 to 180 to match hydromt-sfincs
        if ds["lon"].min() > 180:
            ds["lon"] = ds["lon"] - 360

        return ds
