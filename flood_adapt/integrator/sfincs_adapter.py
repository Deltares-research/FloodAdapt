from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from cht_tide.read_bca import SfincsBoundary
from cht_tide.tide_predict import predict
from hydromt_sfincs import SfincsModel

from flood_adapt.object_model.hazard.event.event import EventModel
from flood_adapt.object_model.hazard.measure.floodwall import FloodWallModel

# from flood_adapt.object_model.validate.config import validate_existence_root_folder


class SfincsAdapter:
    def __init__(self, model_root: Optional[str] = None):
        """Loads overland sfincs model based on a root directory.

        Args:
            model_root (str, optional): Root directory of overland sfincs model. Defaults to None.
        """
        # Check if model root exists
        # if validate_existence_root_folder(model_root):
        #    self.model_root = model_root

        self.sf_model = SfincsModel(root=model_root, mode="r+")
        self.sf_model.read()

    def set_timing(self, event: EventModel):
        """Changes model reference times based on event time series."""

        # Get start and end time of event based on different templates
        if event.template == "Synthetic":
            tstart = datetime.strptime(event.time.start_time, "%Y%m%d %H%M%S")
            tstop = datetime.strptime(event.time.end_time, "%Y%m%d %H%M%S")
        else:
            tstart = event.time.start_time
            tstop = event.time.end_time
        # Update timing of the model
        self.sf_model.set_config("tref", tstart)
        self.sf_model.set_config("tstart", tstart)
        self.sf_model.set_config("tstop", tstop)

    def add_wind_forcing(self, timeseries=None, const_mag=None, const_dir=None):
        self.sf_model.setup_wind_forcing(
            timeseries=timeseries, const_mag=const_mag, const_dir=const_dir
        )

    def add_wind_forcing_from_grid(self, wind_u, wind_v):
        self.sf_model.setup_wind_forcing_from_grid(wind_u=wind_u, wind_v=wind_v)

    def add_pressure_forcing_from_grid(self, press):
        self.sf_model.setup_pressure_forcing_from_grid(press=press)

    def add_precip_forcing_from_grid(self, precip):
        self.sf_model.setup_precip_forcing_from_grid(precip=precip, aggregate=False)

    def add_precip_forcing(self, precip=None, const_precip=None):
        self.sf_model.setup_precip_forcing(precip=precip, const_precip=const_precip)

    def add_wl_bc(self, df_ts: pd.DataFrame):
        """Changes waterlevel of overland sfincs model based on new waterlevel time series.

        Parameters
        ----------
        df_ts : pd.DataFrame
            time series of water level, index should be Pandas DateRange
        """

        # Determine bnd points from reference overland model
        gdf_locs = self.sf_model.forcing["bzs"].vector.to_gdf()
        gdf_locs.crs = self.sf_model.crs

        # Go from 1 timeseries to timeseries for all boundary points
        for i in range(1, len(gdf_locs)):
            df_ts[i + 1] = df_ts[1]

        # HydroMT function: set waterlevel forcing from time series
        self.sf_model.set_forcing_1d(
            name="bzs", df_ts=df_ts, gdf_locs=gdf_locs, merge=False
        )

    def add_bzs_from_bca(self, event: EventModel):
        """Convert tidal constituents from bca file to waterlevel timeseries that can be read in by hydromt_sfincs"""

        sb = SfincsBoundary()
        sb.read_flow_boundary_points(Path(self.sf_model.root).joinpath("sfincs.bnd"))
        sb.read_astro_boundary_conditions(
            Path(self.sf_model.root).joinpath("sfincs.bca")
        )

        times = pd.date_range(
            start=event.time.start_time,
            end=event.time.end_time,
            freq="10T",
        )

        for bnd_ii in range(len(sb.flow_boundary_points)):
            tide_ii = predict(sb.flow_boundary_points[bnd_ii].astro, times)
            if bnd_ii == 0:
                wl_df = pd.DataFrame(data={1: tide_ii}, index=times)
            else:
                wl_df[bnd_ii + 1] = tide_ii

        # Determine bnd points from reference overland model
        gdf_locs = self.sf_model.forcing["bzs"].vector.to_gdf()
        gdf_locs.crs = self.sf_model.crs

        # HydroMT function: set waterlevel forcing from time series
        self.sf_model.set_forcing_1d(
            name="bzs", df_ts=wl_df, gdf_locs=gdf_locs, merge=False
        )

    def add_dis_bc(self, df_ts: pd.DataFrame):
        """Changes discharge of overland sfincs model based on new discharge time series.

        Parameters
        ----------
        df_ts : pd.DataFrame
            time series of discharge, index should be Pandas DateRange
        """

        # Determine bnd points from reference overland model
        gdf_locs = self.sf_model.forcing["dis"].vector.to_gdf()
        gdf_locs.crs = self.sf_model.crs

        # Go from 1 timeseries to timeseries for all boundary points
        for i in range(1, len(gdf_locs)):
            df_ts[i] = df_ts[i]

        # HydroMT function: set waterlevel forcing from time series
        self.sf_model.set_forcing_1d(
            name="dis", df_ts=df_ts, gdf_locs=gdf_locs, merge=False
        )

    def add_floodwall(self, floodwall: FloodWallModel):
        """Adds floodwall to sfincs model.

        Parameters
        ----------
        floodwall : FloodWallModel
            floodwall information
        """

        # HydroMT function: get geodataframe from filename
        # TODO polygon file should be txt file with extension xy (!)
        gdf_floodwall = self.sf_model.data_catalog.get_geodataframe(
            floodwall.polygon_file, geom=self.sf_model.region, crs=self.sf_model.crs
        )

        # Add floodwall attributes to geodataframe
        gdf_floodwall["name"] = floodwall.name
        gdf_floodwall["z"] = floodwall.elevation
        gdf_floodwall["par1"] = 0.6

        # HydroMT function: create floodwall
        self.sf_model.create_structures(
            gdf_structures=gdf_floodwall, stype="weir", overwrite=False
        )

    def write_sfincs_model(self, path_out: Path):
        """Write all the files for the sfincs model

        Args:
            path_out (Path): new root of sfincs model
        """
        # Change model root to new folder
        self.sf_model.set_root(path_out, mode="w+")

        # Write sfincs files in output folder
        self.sf_model.write()

    # def run_sfincs_models(self):
    #      pass

    # def add_floodwall(self, polygon_file: str = None):

    #     #HydroMT function: creates structure from dataframe
    #     #Needs to be completed in hydromt_sfincs
    #     self.sf_model.create_structures(structures_fn=polygon_file, stype='weir', overwrite=False)

    # def add_meteo_bc(self,
    #                  precip_ts: Union[xr.DataArray, pd.DataFrame, Dict[str, pd.DataFrame]] = None
    #                  ):
    #     #HydroMT function: set precipitation from times series
    #     self.sf_model.set_forcing(name='precip',ts=precip_ts,xy=xy_precip)

    # def add_discharge_bc(self,
    #                      dis_ts: Union[xr.DataArray, pd.DataFrame, Dict[str, pd.DataFrame]] = None
    #                      ):
    #     #HydroMT function: set river forcing from times series
    #     self.sf_model.set_forcing_1d(name='dis',ts=dis_ts,xy=self.sf_model.forcing['dis'].vector.to_gdf())
