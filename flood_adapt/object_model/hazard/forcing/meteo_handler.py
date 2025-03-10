from datetime import datetime
from pathlib import Path
from typing import Optional

import cht_meteo
import numpy as np
import xarray as xr
from cht_meteo.dataset import MeteoDataset

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
        # Create GFS dataset
        self.dataset = cht_meteo.dataset(
            name="gfs_anl_0p50",
            source="gfs_analysis_0p50",
            path=self.dir,
            lon_range=(self.site.attrs.lon - 10, self.site.attrs.lon + 10),
            lat_range=(self.site.attrs.lat - 10, self.site.attrs.lat + 10),
        )
        # quick fix for sites near the 0 degree longitude -> shift the meteo download area either east or west of the 0 degree longitude
        # TODO implement a good solution to this in cht_meteo
        self.dataset.lon_range = self._shift_grid_to_positive_lon(self.dataset)

    def download(self, time: TimeModel):
        # Download and collect data
        time_range = self.get_time_range(time)

        self.dataset.download(time_range=time_range)

    def read(self, time: TimeModel) -> xr.Dataset:
        self.download(time)
        time_range = self.get_time_range(time)
        ds = self.dataset.collect(time_range=time_range)

        if ds is None:
            raise FileNotFoundError(
                f"No meteo files found in meteo directory {self.dir}"
            )

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

    @staticmethod
    def get_time_range(time: TimeModel) -> tuple:
        t0 = time.start_time
        t1 = time.end_time
        if not isinstance(t0, datetime):
            t0 = datetime.strptime(t0, "%Y%m%d %H%M%S")
        if not isinstance(t1, datetime):
            t1 = datetime.strptime(t1, "%Y%m%d %H%M%S")
        time_range = (t0, t1)
        return time_range

    @staticmethod
    def _shift_grid_to_positive_lon(grid: MeteoDataset):
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
