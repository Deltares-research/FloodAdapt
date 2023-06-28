from pathlib import Path
from typing import Optional

import pandas as pd
from hydromt_sfincs import SfincsModel

from flood_adapt.object_model.hazard.event.event import EventModel
from flood_adapt.object_model.hazard.measure.floodwall import FloodWallModel
from flood_adapt.object_model.hazard.measure.green_infrastructure import (
    GreenInfrastructureModel,
)

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
        tstart = event.time.start_time
        tstop = event.time.end_time

        # Update timing of the model
        self.sf_model.set_config("tref", tstart)
        self.sf_model.set_config("tstart", tstart)
        self.sf_model.set_config("tstop", tstop)

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
            df_ts[i + 1] = df_ts[i]

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

    def add_green_infrastructure(
        self, green_infrastructure: GreenInfrastructureModel, measure_path: Path
    ):
        """Adds green infrastructure to sfincs model.

        Parameters
        ----------
        green_infrastructure : GreenInfrastructureModel
            Green infrastructure information
        measure_path: Path
            Path of the measure folder
        """

        # HydroMT function: get geodataframe from filename
        polygon_file = measure_path.joinpath(green_infrastructure.polygon_file)
        gdf_green_infra = self.sf_model.data_catalog.get_geodataframe(
            polygon_file,
            geom=self.sf_model.region,
            crs=self.sf_model.crs,
        )

        # Determine volume capacity of green infrastructure

        if green_infrastructure.height.value != 0.0:
            height = (
                green_infrastructure.height.convert("m")
                * green_infrastructure.percent_area
            )
            volume = None
        elif green_infrastructure.volume.value != 0.0:
            height = None
            volume = green_infrastructure.volume.convert("m3")

        # HydroMT function: create storage volume
        self.sf_model.setup_storage_volume(
            storage_locs=gdf_green_infra, volume=volume, height=height, merge=True
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
