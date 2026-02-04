import logging
from datetime import datetime
from pathlib import Path

import cht_meteo
import numpy as np
import xarray as xr
from cht_meteo.dataset import MeteoDataset

from flood_adapt.objects.forcing.time_frame import TimeFrame

logger = logging.getLogger(__name__)


class MeteoHandler:
    def __init__(self, dir: Path, lat: float, lon: float) -> None:
        self.dir: Path = dir
        self.dir.mkdir(parents=True, exist_ok=True)

        # Create GFS dataset
        self.dataset = cht_meteo.dataset(
            name="gfs_anl_0p50",
            source="gfs_analysis_0p50",
            path=self.dir,
            lon_range=(lon - 10, lon + 10),
            lat_range=(lat - 10, lat + 10),
        )
        # quick fix for sites near the 0 degree longitude -> shift the meteo download area either east or west of the 0 degree longitude
        # TODO implement a good solution to this in cht_meteo
        self.dataset.lon_range = self._shift_grid_to_positive_lon(self.dataset)

    def download(self, time: TimeFrame) -> None:
        # Download and collect data
        time_range = self.get_time_range(time)
        self.dataset.download(time_range=time_range)

    def read(self, time: TimeFrame, retries: int = 5) -> xr.Dataset:
        for i in range(retries):
            self.download(time)
            time_range = self.get_time_range(time)
            ds = self.dataset.collect(time_range=time_range)
            if ds is not None:
                break  # Exit the loop if data is found
            else:
                msg = f"No meteo files found in meteo directory {self.dir}"
                logger.warning(f"{msg}. Retrying {i+1}/{retries}...")
                if i == retries - 1:
                    raise FileNotFoundError(f"{msg} after {retries} retries.")

        # rename coordinates to time, x, y, press_msl, precip, wind10_u, wind10_v
        # as required by hydromt-sfincs
        # variables: ['wind10_u' (m/s), 'wind10_v' (m/s)]
        ds = ds.rename(
            {
                "lon": "x",
                "lat": "y",
                "barometric_pressure": "press_msl",
                "precipitation": "precip",
                "wind_u": "wind10_u",
                "wind_v": "wind10_v",
            }
        )

        ds.raster.set_crs(4326)

        # Convert the longitude to -180 to 180 to match hydromt-sfincs
        if ds["x"].min() > 180:
            ds["x"] = ds["x"] - 360

        return ds

    @staticmethod
    def get_time_range(time: TimeFrame) -> tuple:
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
                    -1,
                ]
            else:
                grid.lon_range = [
                    1,
                    grid.lon_range[1] - grid.lon_range[0] + 1,
                ]
        return grid.lon_range
