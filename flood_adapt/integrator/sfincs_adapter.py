import gc
import logging
import os
import subprocess
from pathlib import Path
from typing import Union

import geopandas as gpd
import hydromt_sfincs.utils as utils
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import xarray as xr
from cht_tide.read_bca import SfincsBoundary
from cht_tide.tide_predict import predict
from hydromt_sfincs import SfincsModel
from hydromt_sfincs.quadtree import QuadtreeGrid
from noaa_coops.station import COOPSAPIError
from numpy import matlib

import flood_adapt.config as FloodAdapt_config
from flood_adapt.integrator.interface.hazard_adapter import HazardData, IHazardAdapter
from flood_adapt.log import FloodAdaptLogging
from flood_adapt.object_model.hazard.event.forcing.discharge import (
    DischargeConstant,
    DischargeSynthetic,
    IDischarge,
)
from flood_adapt.object_model.hazard.event.forcing.rainfall import (
    IRainfall,
    RainfallConstant,
    RainfallFromModel,
    RainfallSynthetic,
)
from flood_adapt.object_model.hazard.event.forcing.waterlevels import (
    IWaterlevel,
    WaterlevelFromCSV,
    WaterlevelFromGauged,
    WaterlevelFromModel,
    WaterlevelSynthetic,
)
from flood_adapt.object_model.hazard.event.forcing.wind import (
    IWind,
    WindConstant,
    WindFromModel,
    WindFromTrack,
    WindSynthetic,
)
from flood_adapt.object_model.hazard.event.hurricane import (
    HurricaneEvent,
)
from flood_adapt.object_model.hazard.interface.events import IEvent, IEventModel, Mode
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingType,
    IForcing,
)
from flood_adapt.object_model.hazard.measure.floodwall import FloodWall
from flood_adapt.object_model.hazard.measure.green_infrastructure import (
    GreenInfrastructure,
)
from flood_adapt.object_model.hazard.measure.hazard_measure import HazardMeasure
from flood_adapt.object_model.hazard.measure.pump import Pump
from flood_adapt.object_model.hazard.physical_projection import PhysicalProjection
from flood_adapt.object_model.interface.database import IDatabase
from flood_adapt.object_model.interface.measures import HazardType
from flood_adapt.object_model.interface.projections import PhysicalProjectionModel
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.interface.site import ISite
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulLength,
    UnitTypesDischarge,
    UnitTypesLength,
    UnitTypesVolume,
)
from flood_adapt.object_model.utils import cd


class SfincsData(HazardData):
    flood_map = "flood_map"
    boundary = "boundary"
    water_level_map = "water_level_map"
    mask = "mask"
    bed_level = "bed_level"
    grid = "grid"


class SfincsAdapter(IHazardAdapter):
    _logger: logging.Logger
    _database: IDatabase

    _site: ISite
    _scenario: IScenario
    _model: SfincsModel

    def __init__(self, model_root: str, database: IDatabase = None):
        """Load overland sfincs model based on a root directory.

        Args:
            database (IDatabase): Reference to the database containing all objectmodels and site specific information.
            model_root (str): Root directory of overland sfincs model.
        """
        if database is None:
            import flood_adapt.dbs_controller as db

            database = db.Database()

        self._logger = FloodAdaptLogging.getLogger(__name__)
        self._database = database
        self._model = SfincsModel(root=model_root, mode="r+", logger=self._logger)
        self._model.read()
        self._site = database.site

    def __del__(self):
        """Close the log file associated with the logger and clean up file handles."""
        if hasattr(self, "_logger") and hasattr(self._logger, "handlers"):
            # Close the log file associated with the logger
            for handler in self._logger.handlers:
                handler.close()
            self._logger.handlers.clear()
        # Use garbage collector to ensure file handles are properly cleaned up
        gc.collect()

    def __enter__(self):
        """Enter the context manager and prepare the model for usage. Exiting the context manager will call __exit__ and free resources.

        Returns
        -------
            SfincsAdapter: The SfincsAdapter object.

        Usage:
            with SfincsAdapter(model_root) as model:
                model.read()
                ...
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the context manager, close loggers and free resources. Always gets called when exiting the context manager, even if an exception occurred.

        Usage:
            with SfincsAdapter(model_root) as model:
                model.read()
                ...
        """
        # Explicitly delete self to ensure resources are freed
        del self

        # Return False to propagate/reraise any exceptions that occurred in the with block
        # Return True to suppress any exceptions that occurred in the with block
        return False

    ### HAZARD ADAPTER METHODS ###
    def read(self):
        """Read the sfincs model."""
        self._model.read()

    def write(self, path_out: Union[str, os.PathLike]):
        """Write the sfincs model."""
        with cd(path_out):
            self._model.write()

    def execute(self, sim_path=None, strict=True) -> bool:
        """
        Run the sfincs executable in the specified path.

        Parameters
        ----------
        sim_path : str
            Path to the simulation folder.
            Default is None, in which case the model root is used.
        strict : bool, optional
            True: raise an error if the model fails to run.
            False: log a warning.
            Default is True.

        Returns
        -------
        bool
            True if the model ran successfully, False otherwise.

        """
        if not FloodAdapt_config.get_system_folder():
            raise ValueError(
                """
                SYSTEM_FOLDER environment variable is not set. Set it by calling FloodAdapt_config.set_system_folder() and provide the path.
                The path should be a directory containing folders with the model executables
                """
            )

        sfincs_exec = FloodAdapt_config.get_system_folder() / "sfincs" / "sfincs.exe"
        sim_path = sim_path or self._model.root

        with cd(sim_path):
            sfincs_log = "sfincs.log"
            with FloodAdaptLogging.to_file(file_path=sfincs_log):
                process = subprocess.run(
                    sfincs_exec,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                self._logger.debug(process.stdout)

        if process.returncode != 0:
            # Remove all files in the simulation folder except for the log files
            for subdir, _, files in os.walk(sim_path):
                for file in files:
                    if not file.endswith(".log"):
                        os.remove(os.path.join(subdir, file))

            # Remove all empty directories in the simulation folder (so only folders with log files remain)
            for subdir, _, files in os.walk(sim_path):
                if not files:
                    os.rmdir(subdir)

            if strict:
                raise RuntimeError(f"SFINCS model failed to run in {sim_path}.")
            else:
                self._logger.error(f"SFINCS model failed to run in {sim_path}.")

        return process.returncode == 0

    def run(self, scenario: IScenario):
        """Run the whole workflow (Preprocess, process and postprocess) for a given scenario."""
        self._scenario = scenario

        self._preprocess()
        self._process()
        self._postprocess()

        self._scenario = None

    def set_timing(self, event: IEventModel):
        """Set model reference times based on event time series."""
        # Get start and end time of event
        tstart = event.time.start_time
        tstop = event.time.end_time

        # Update timing of the model
        self._model.set_config("tref", tstart)
        self._model.set_config("tstart", tstart)
        self._model.set_config("tstop", tstop)

    def add_forcing(self, forcing: IForcing):
        """Get forcing data and add it to the sfincs model."""
        match forcing._type:
            case ForcingType.WIND:
                self._add_forcing_wind(forcing)
            case ForcingType.RAINFALL:
                self._add_forcing_rain(forcing)
            case ForcingType.DISCHARGE:
                self._add_forcing_discharge(forcing)
            case ForcingType.WATERLEVEL:
                self._add_forcing_waterlevels(forcing)
            case _:
                self._logger.warning(
                    f"Skipping unsupported forcing type {forcing.__class__.__name__}"
                )
                return

    def add_measure(self, measure: HazardMeasure):
        """Get measure data and add it to the sfincs model."""
        match measure.attrs.type:
            case HazardType.floodwall:
                self._add_measure_floodwall(measure)
            case HazardType.greening:
                self._add_measure_greeninfra(measure)
            case HazardType.pump:
                self._add_measure_pump(measure)
            case _:
                self._logger.warning(
                    f"Skipping unsupported measure type {measure.__class__.__name__}"
                )
                return

    def add_projection(self, projection: PhysicalProjection):
        """Get forcing data currently in the sfincs model and add the projection it."""
        self._add_wl_bc(self.get_water_levels() + projection.attrs.sea_level_rise)

        # TODO investigate how/if to add subsidence to model
        # projection.attrs.subsidence

        rainfall = self.get_rainfall() + projection.attrs.rainfall_increase
        self._add_precip_forcing(rainfall)

        # TODO investigate how/if to add storm frequency increase to model
        # projection.attrs.storm_frequency_increase

    def has_run_check(self) -> bool:
        """Check if the model has run successfully.

        Returns
        -------
        bool
            _description_
        """
        floodmaps = self._get_flood_map_path()

        # Iterate to all needed flood map files to check if they exists
        checks = []
        for map in floodmaps:
            checks.append(map.exists())

        return all(checks)

    ### PUBLIC GETTERS - Can be called from outside of this class ###
    def get_mask(self):
        """Get mask with inactive cells from model."""
        mask = self._model.grid["msk"]
        return mask

    def get_bedlevel(self):
        """Get bed level from model."""
        self._model.read_results()
        zb = self._model.results["zb"]
        return zb

    def get_model_boundary(self) -> gpd.GeoDataFrame:
        """Get bounding box from model."""
        return self._model.region

    def get_model_grid(self) -> QuadtreeGrid:
        """Get grid from model.

        Returns
        -------
        QuadtreeGrid
            QuadtreeGrid with the model grid
        """
        return self._model.quadtree

    ### PRIVATE METHODS - Should not be called from outside of this class ###
    def _preprocess(self):
        sim_paths = self._get_simulation_paths()
        events = (
            [self._scenario.attrs.event]
            if isinstance(list, self._scenario.attrs.event)
            else self._scenario.attrs.event
        )
        for ii, name in enumerate(events):
            event: IEvent = self._database.events.get(name)

            self.set_timing(event.attrs)

            # run offshore model or download wl data,
            # copy all required files to the simulation folder
            # write forcing data to event object
            event.process(self._scenario)

            for forcing in event.attrs.forcings.values():
                self.add_forcing(forcing)

            for measure in self._scenario.attrs.strategy:
                self.add_measure(measure)

            for projection in self._scenario.attrs.projection:
                self.add_projection(projection)

            # add observation points from site.toml
            self._add_obs_points()

            # write sfincs model in output destination
            self._write_sfincs_model(path_out=sim_paths[ii])

    def _process(self):
        sim_paths = self._get_simulation_paths()
        results = []
        for simulation_path in sim_paths:
            results.append(self.execute(simulation_path))

        # Indicator that hazard has run
        # TODO add func to store this in the dbs scenario
        self._scenario.has_run = all(results)

    def _postprocess(self):
        if not self.has_run_check(self._scenario):
            raise RuntimeError("SFINCS was not run successfully!")

        mode = self._database.events.get(self._scenario.attrs.event).get_mode()
        if mode == Mode.single_event:
            # Write flood-depth map geotiff
            self._write_floodmap_geotiff()
            # Write watel-level time-series
            self._plot_wl_obs()
            # Write max water-level netcdf
            self._write_water_level_map()
        elif mode == Mode.risk:
            # Write max water-level netcdfs per return period
            self._calculate_rp_floodmaps()

        # Save flood map paths in object
        self._get_flood_map_path()

    ### FORCING HELPERS ###
    def _add_forcing_wind(
        self,
        forcing: IWind,
    ):
        """Add spatially constant wind forcing to sfincs model. Use timeseries or a constant magnitude and direction.

        Parameters
        ----------
        timeseries : Union[str, os.PathLike], optional
            path to file of timeseries file (.csv) which has three columns: time, magnitude and direction, by default None
        const_mag : float, optional
            magnitude of time-invariant wind forcing [m/s], by default None
        const_dir : float, optional
            direction of time-invariant wind forcing [deg], by default None
        """
        if isinstance(forcing, WindConstant):
            self._model.setup_wind_forcing(
                timeseries=None,
                const_mag=forcing.speed,
                const_dir=forcing.direction,
            )
        elif isinstance(forcing, WindSynthetic):
            self._model.setup_wind_forcing(
                timeseries=forcing.path, const_mag=None, const_dir=None
            )
        elif isinstance(forcing, WindFromModel):
            # TODO check with @gundula
            self._add_wind_forcing_from_grid(forcing.path)
        elif isinstance(forcing, WindFromTrack):
            # TODO check with @gundula
            self._set_config_spw(forcing.path)
        else:
            self._logger.warning(
                f"Unsupported wind forcing type: {forcing.__class__.__name__}"
            )
            return

    def _add_forcing_rain(self, forcing: IRainfall):
        """Add spatially constant rain forcing to sfincs model. Use timeseries or a constant magnitude.

        Parameters
        ----------
        timeseries : Union[str, os.PathLike], optional
            path to file of timeseries file (.csv) which has two columns: time and precipitation, by default None
        const_intensity : float, optional
            time-invariant precipitation intensity [mm_hr], by default None
        """
        if isinstance(forcing, RainfallConstant):
            self._model.setup_precip_forcing(
                timeseries=None,
                magnitude=forcing.intensity,
            )

        elif isinstance(forcing, RainfallSynthetic):
            self._model.add_precip_forcing(timeseries=forcing.get_data())

        elif isinstance(forcing, RainfallFromModel):
            self._model.setup_precip_forcing_from_grid(precip=forcing.get_data())
        else:
            self._logger.warning(
                f"Unsupported rainfall forcing type: {forcing.__class__.__name__}"
            )
            return

    def _add_forcing_discharge(self, forcing: IDischarge):
        """Add spatially constant discharge forcing to sfincs model. Use timeseries or a constant magnitude.

        Parameters
        ----------
        timeseries : Union[str, os.PathLike], optional
            path to file of timeseries file (.csv) which has two columns: time and discharge, by default None
        const_discharge : float, optional
            time-invariant discharge magnitude [m3/s], by default None
        """
        # TODO investigate where to include rivers from site.toml
        if isinstance(forcing, DischargeConstant):
            self._model.setup_discharge_forcing(
                timeseries=None,
                magnitude=forcing.discharge,
            )
        elif isinstance(forcing, DischargeSynthetic):
            self._add_dis_bc(forcing.path)
        else:
            self._logger.warning(
                f"Unsupported discharge forcing type: {forcing.__class__.__name__}"
            )
            return

    def _add_forcing_waterlevels(self, forcing: IWaterlevel):
        if isinstance(
            forcing, (WaterlevelSynthetic, WaterlevelFromCSV, WaterlevelFromGauged)
        ):
            self._add_wl_bc(forcing.get_data())
        elif isinstance(forcing, WaterlevelFromModel):
            self._add_wl_bc(forcing.get_data())
            self._turn_off_bnd_press_correction()
        else:
            self._logger.warning(
                f"Unsupported waterlevel forcing type: {forcing.__class__.__name__}"
            )

    ### MEASURES HELPERS ###
    def _add_measure_floodwall(self, floodwall: FloodWall):
        """Add floodwall to sfincs model.

        Parameters
        ----------
        floodwall : FloodWallModel
            floodwall information
        """
        # HydroMT function: get geodataframe from filename
        polygon_file = self._database.input_path.joinpath(floodwall.attrs.polygon_file)
        gdf_floodwall = self._model.data_catalog.get_geodataframe(
            polygon_file, geom=self._model.region, crs=self._model.crs
        )

        # Add floodwall attributes to geodataframe
        gdf_floodwall["name"] = floodwall.attrs.name
        if (gdf_floodwall.geometry.type == "MultiLineString").any():
            gdf_floodwall = gdf_floodwall.explode()
        # TODO: Choice of height data from file or uniform height and column name with height data should be adjustable in the GUI
        try:
            heights = [
                float(
                    UnitfulLength(
                        value=float(height),
                        units=self._site.attrs.gui.default_length_units,
                    ).convert(UnitTypesLength("meters"))
                )
                for height in gdf_floodwall["z"]
            ]
            gdf_floodwall["z"] = heights
            logging.info("Using floodwall height from shape file.")
        except Exception:
            logging.warning(
                f"""Could not use height data from file due to missing ""z""-column or missing values therein.\n
                Using uniform height of {floodwall.attrs.elevation.convert(UnitTypesLength("meters"))} meters instead."""
            )
            gdf_floodwall["z"] = floodwall.attrs.elevation.convert(
                UnitTypesLength("meters")
            )

        # par1 is the overflow coefficient for weirs
        gdf_floodwall["par1"] = 0.6

        # HydroMT function: create floodwall
        self._model.setup_structures(structures=gdf_floodwall, stype="weir", merge=True)

    def _add_measure_greeninfra(self, green_infrastructure: GreenInfrastructure):
        # HydroMT function: get geodataframe from filename
        if green_infrastructure.attrs.selection_type == "polygon":
            polygon_file = self._database.input_path.joinpath(
                green_infrastructure.attrs.polygon_file
            )
        elif green_infrastructure.attrs.selection_type == "aggregation_area":
            # TODO this logic already exists in the Database controller but cannot be used due to cyclic imports
            # Loop through available aggregation area types
            for aggr_dict in self._site.attrs.fiat.aggregation:
                # check which one is used in measure
                if (
                    not aggr_dict.name
                    == green_infrastructure.attrs.aggregation_area_type
                ):
                    continue
                # load geodataframe
                aggr_areas = gpd.read_file(
                    self._database.static_path / "site" / aggr_dict.file,
                    engine="pyogrio",
                ).to_crs(4326)
                # keep only aggregation area chosen
                polygon_file = aggr_areas.loc[
                    aggr_areas[aggr_dict.field_name]
                    == green_infrastructure.attrs.aggregation_area_name,
                    ["geometry"],
                ].reset_index(drop=True)
        else:
            raise ValueError(
                f"The selection type: {green_infrastructure.attrs.selection_type} is not valid"
            )

        gdf_green_infra = self._model.data_catalog.get_geodataframe(
            polygon_file,
            geom=self._model.region,
            crs=self._model.crs,
        )

        # Make sure no multipolygons are there
        gdf_green_infra = gdf_green_infra.explode()

        # Volume is always already calculated and is converted to m3 for SFINCS
        height = None
        volume = green_infrastructure.attrs.volume.convert(UnitTypesVolume("m3"))

        # HydroMT function: create storage volume
        self._model.setup_storage_volume(
            storage_locs=gdf_green_infra, volume=volume, height=height, merge=True
        )

    def _add_measure_pump(self, pump: Pump):
        """Add pump to sfincs model.

        Parameters
        ----------
        pump : PumpModel
            pump information
        """
        polygon_file = self._database.input_path.joinpath(pump.attrs.polygon_file)
        # HydroMT function: get geodataframe from filename
        gdf_pump = self._model.data_catalog.get_geodataframe(
            polygon_file, geom=self._model.region, crs=self._model.crs
        )

        # HydroMT function: create floodwall
        self._model.setup_drainage_structures(
            structures=gdf_pump,
            stype="pump",
            discharge=pump.attrs.discharge.convert(UnitTypesDischarge("m3/s")),
            merge=True,
        )

    ### PROJECTIONS HELPERS - not needed at the moment ###

    ##### OLD CODE BELOW #####
    # @Gundula: I have renamed some the functions and added comments to some that explain when they were called in the original hazard.py just to keep track.
    # Im not super familiar with hydromt_sfincs and its functions, so I have not changed the logic of the functions, only the names and comments.
    # It could be the case that some of the functions in here are not needed anymore, but we can always remove them later if needed.

    # I have also added a '_' to the start of all functions I see as private.
    # Public functions can be called from outside of the class, all private functions should not be called from outside of the class.
    # (even though python does not care and will allow it anyways, we can still follow the convention just to make it clear)

    ### SFINCS SETTERS ###

    def _set_config_spw(self, spw_name: str):
        self._model.set_config("spwfile", spw_name)

    def _turn_off_bnd_press_correction(self):
        self._model.set_config("pavbnd", -9999)

    ### ADD TO SFINCS ###
    # @Gundula functions starting with `add` should not blindly overwrite data in sfincs, but read data from the model, add something to it, then set the model again.
    # This is to ensure that we do not overwrite any existing data in the model.
    # (maybe this is what hydromt_sfincs already does, but just checking with you)
    def _add_obs_points(self):
        """Add observation points provided in the site toml to SFINCS model."""
        if self._site.attrs.obs_point is not None:
            logging.info("Adding observation points to the overland flood model...")

            obs_points = self._site.attrs.obs_point
            names = []
            lat = []
            lon = []
            for pt in obs_points:
                names.append(pt.name)
                lat.append(pt.lat)
                lon.append(pt.lon)

            # create GeoDataFrame from obs_points in site file
            df = pd.DataFrame({"name": names})
            gdf = gpd.GeoDataFrame(
                df, geometry=gpd.points_from_xy(lon, lat), crs="EPSG:4326"
            )

            # Add locations to SFINCS file
            self._model.setup_observation_points(locations=gdf, merge=False)

    def _add_wind_forcing_from_grid(self, ds: xr.DataArray):
        # if self.event.attrs.template != "Historical_hurricane":
        # if self.event.attrs.wind.source == "map":
        # add to overland & offshore
        """Add spatially varying wind forcing to sfincs model.

        Parameters
        ----------
        ds : xr.DataArray
            Dataarray which should contain:
            - wind_u: eastward wind velocity [m/s]
            - wind_v: northward wind velocity [m/s]
            - spatial_ref: CRS
        """
        self._model.setup_wind_forcing_from_grid(wind=ds)

    def _add_pressure_forcing_from_grid(self, ds: xr.DataArray):
        # if self.event.attrs.template == "Historical_offshore":
        # if self.event.attrs.wind.source == "map":
        # add to offshore only?
        """Add spatially varying barometric pressure to sfincs model.

        Parameters
        ----------
        ds : xr.DataArray
            Dataarray which should contain:
            - press: barometric pressure [Pa]
            - spatial_ref: CRS
        """
        self._model.setup_pressure_forcing_from_grid(press=ds)

    def _add_precip_forcing(
        self, timeseries: Union[str, os.PathLike] = None, const_precip: float = None
    ):
        # rainfall from file
        # synthetic rainfall
        # constant rainfall
        """Add spatially uniform precipitation to sfincs model.

        Parameters
        ----------
        precip : Union[str, os.PathLike], optional
            timeseries file of precipitation (.csv) which has two columns: time and precipitation, by default None
        const_precip : float, optional
            time-invariant precipitation magnitude [mm_hr], by default None
        """
        # Add precipitation to SFINCS model
        self._model.setup_precip_forcing(timeseries=timeseries, magnitude=const_precip)

    def _add_wl_bc(self, df_ts: pd.DataFrame):
        # ALL
        """Add waterlevel dataframe to sfincs model.

        Parameters
        ----------
        df_ts : pd.DataFrame
            Dataframe with waterlevel time series at every boundary point (index of the dataframe should be time and every column should be an integer starting with 1)
        """
        # Determine bnd points from reference overland model
        gdf_locs = self._model.forcing["bzs"].vector.to_gdf()
        gdf_locs.crs = self._model.crs

        if len(df_ts.columns) == 1:
            # Go from 1 timeseries to timeseries for all boundary points
            for i in range(1, len(gdf_locs)):
                df_ts[i + 1] = df_ts[1]

        # HydroMT function: set waterlevel forcing from time series
        self._model.set_forcing_1d(
            name="bzs", df_ts=df_ts, gdf_locs=gdf_locs, merge=False
        )

    def _add_bzs_from_bca(
        self, event: IEventModel, physical_projection: PhysicalProjectionModel
    ):
        # ONLY offshore models
        """Convert tidal constituents from bca file to waterlevel timeseries that can be read in by hydromt_sfincs."""
        sb = SfincsBoundary()
        sb.read_flow_boundary_points(Path(self._model.root).joinpath("sfincs.bnd"))
        sb.read_astro_boundary_conditions(Path(self._model.root).joinpath("sfincs.bca"))

        times = pd.date_range(
            start=event.time.start_time,
            end=event.time.end_time,
            freq="10T",
        )

        # Predict tidal signal and add SLR
        for bnd_ii in range(len(sb.flow_boundary_points)):
            tide_ii = (
                predict(sb.flow_boundary_points[bnd_ii].astro, times)
                + event.water_level_offset.convert(UnitTypesLength("meters"))
                + physical_projection.sea_level_rise.convert(UnitTypesLength("meters"))
            )

            if bnd_ii == 0:
                wl_df = pd.DataFrame(data={1: tide_ii}, index=times)
            else:
                wl_df[bnd_ii + 1] = tide_ii

        # Determine bnd points from reference overland model
        gdf_locs = self._model.forcing["bzs"].vector.to_gdf()
        gdf_locs.crs = self._model.crs

        # HydroMT function: set waterlevel forcing from time series
        self._model.set_forcing_1d(
            name="bzs", df_ts=wl_df, gdf_locs=gdf_locs, merge=False
        )

    def _add_dis_bc(self, list_df: pd.DataFrame, site_river: list):
        # Should always be called if rivers in site > 0
        # then use site as default values, and overwrite if discharge is provided.
        """Add discharge to overland sfincs model based on new discharge time series.

        Parameters
        ----------
        df_ts : pd.DataFrame
            time series of discharge, index should be Pandas DateRange
        """
        # Determine bnd points from reference overland model
        # ASSUMPTION: Order of the rivers is the same as the site.toml file
        if np.any(list_df):
            gdf_locs = self._model.forcing["dis"].vector.to_gdf()
            gdf_locs.crs = self._model.crs

            if len(list_df.columns) != len(gdf_locs):
                self._logger.error(
                    """The number of rivers of the site.toml does not match the
                              number of rivers in the SFINCS model. Please check the number
                              of coordinates in the SFINCS *.src file."""
                )
                raise ValueError(
                    "Number of rivers in site.toml and SFINCS template model not compatible"
                )

            # Test order of rivers is the same in the site file as in the SFICNS model
            for ii, river in enumerate((site_river)):
                if not (
                    np.abs(gdf_locs.geometry[ii + 1].x - river.x_coordinate) < 5
                    and np.abs(gdf_locs.geometry[ii + 1].y - river.y_coordinate) < 5
                ):
                    self._logger.error(
                        """The location and/or order of rivers in the site.toml does not match the
                                locations and/or order of rivers in the SFINCS model. Please check the
                                coordinates and their order in the SFINCS *.src file and ensure they are
                                consistent with the coordinates and order orf rivers in the site.toml file."""
                    )
                    raise ValueError(
                        f"Incompatible river coordinates for river: {river.name}.\nsite.toml: ({river.x_coordinate}, {river.y_coordinate})\nSFINCS template model ({gdf_locs.geometry[ii + 1].x}, {gdf_locs.geometry[ii + 1].y})."
                    )

            self._model.setup_discharge_forcing(
                timeseries=list_df, locations=gdf_locs, merge=False
            )

    def _add_forcing_spw(
        self,
        historical_hurricane: HurricaneEvent,
        database_path: Path,
        model_dir: Path,
    ):
        """Add spiderweb forcing to the sfincs model.

        Parameters
        ----------
        historical_hurricane : HistoricalHurricane
            Information of the historical hurricane event
        database_path : Path
            Path of the main database
        model_dir : Path
            Output path of the model
        """
        historical_hurricane.make_spw_file(
            database_path=database_path, model_dir=model_dir, site=self._site
        )
        # TODO check with @gundula
        self._set_config_spw(historical_hurricane.spw_file)

    ### PRIVATE GETTERS ###
    def _get_result_path(self, scenario_name: str = None) -> Path:
        if scenario_name is None:
            scenario_name = self._scenario.attrs.name
        path = self._database.scenarios.get_database_path(
            get_input_path=False
        ).joinpath(scenario_name, "Flooding")
        return path

    def _get_simulation_paths(self) -> tuple[list[Path], list[Path]]:
        simulation_paths = []
        simulation_paths_offshore = []
        event = self._database.events.get(self._scenario.attrs.event)
        mode = event.get_mode()
        results_path = self._get_result_path()

        if mode == Mode.single_event:
            simulation_paths.append(
                results_path.joinpath(
                    "simulations",
                    self._site.attrs.sfincs.overland_model,
                )
            )
            # Create a folder name for the offshore model (will not be used if offshore model is not created)
            simulation_paths_offshore.append(
                results_path.joinpath(
                    "simulations",
                    self._site.attrs.sfincs.offshore_model,
                )
            )

        # TODO investigate
        elif mode == Mode.risk:  # risk mode requires an additional folder layer
            for subevent in event.get_subevents():
                simulation_paths.append(
                    results_path.joinpath(
                        "simulations",
                        subevent.attrs.name,
                        self._site.attrs.sfincs.overland_model,
                    )
                )

                # Create a folder name for the offshore model (will not be used if offshore model is not created)
                simulation_paths_offshore.append(
                    results_path.joinpath(
                        "simulations",
                        subevent.attrs.name,
                        self._site.attrs.sfincs.offshore_model,
                    )
                )

        return simulation_paths, simulation_paths_offshore

    def _get_flood_map_path(self) -> list[Path]:
        """_summary_."""
        results_path = self._get_result_path()
        mode = self._database.events.get(self._scenario.attrs.event).get_mode()

        if mode == Mode.single_event:
            map_fn = [results_path.joinpath("max_water_level_map.nc")]

        elif mode == Mode.risk:
            map_fn = []
            for rp in self._site.attrs.risk.return_periods:
                map_fn.append(results_path.joinpath(f"RP_{rp:04d}_maps.nc"))

        return map_fn

    def _get_wl_df_from_offshore_his_results(self) -> pd.DataFrame:
        """Create a pd.Dataframe with waterlevels from the offshore model at the bnd locations of the overland model.

        Returns
        -------
        wl_df: pd.DataFrame
            time series of water level.
        """
        ds_his = utils.read_sfincs_his_results(
            Path(self._model.root).joinpath("sfincs_his.nc"),
            crs=self._model.crs.to_epsg(),
        )
        wl_df = pd.DataFrame(
            data=ds_his.point_zs.to_numpy(),
            index=ds_his.time.to_numpy(),
            columns=np.arange(1, ds_his.point_zs.to_numpy().shape[1] + 1, 1),
        )
        return wl_df

    def _get_zsmax(self):
        """Read zsmax file and return absolute maximum water level over entire simulation."""
        self._model.read_results()
        zsmax = self._model.results["zsmax"].max(dim="timemax")
        zsmax.attrs["units"] = "m"
        return zsmax

    def _get_zs_points(self):
        """Read water level (zs) timeseries at observation points.

        Names are allocated from the site.toml.
        See also add_obs_points() above.
        """
        self._model.read_results()
        da = self._model.results["point_zs"]
        df = pd.DataFrame(index=pd.DatetimeIndex(da.time), data=da.values)

        # get station names from site.toml
        if self._site.attrs.obs_point is not None:
            names = []
            descriptions = []
            obs_points = self._site.attrs.obs_point
            for pt in obs_points:
                names.append(pt.name)
                descriptions.append(pt.description)

        pt_df = pd.DataFrame({"Name": names, "Description": descriptions})
        gdf = gpd.GeoDataFrame(
            pt_df,
            geometry=gpd.points_from_xy(da.point_x.values, da.point_y.values),
            crs=self._model.crs,
        )
        return df, gdf

    ### OUTPUT HELPERS ###
    def _write_floodmap_geotiff(self):
        results_path = self._get_result_path()

        for sim_path in self._get_simulation_paths():
            # read SFINCS model
            with SfincsAdapter(model_root=sim_path) as model:
                # dem file for high resolution flood depth map
                demfile = self._database.static_path.joinpath(
                    "dem", self._site.attrs.dem.filename
                )

                # read max. water level
                zsmax = model._get_zsmax()

                # writing the geotiff to the scenario results folder
                model._write_geotiff(
                    zsmax,
                    demfile=demfile,
                    floodmap_fn=results_path.joinpath(
                        f"FloodMap_{self._scenario.attrs.name}.tif"
                    ),
                )

    def _write_water_level_map(self):
        """Read simulation results from SFINCS and saves a netcdf with the maximum water levels."""
        # read SFINCS model
        sim_paths = self._get_simulation_paths()
        results_path = self._get_result_path()

        # TODO investigate: why only read one model?
        with SfincsAdapter(model_root=sim_paths[0]) as model:
            zsmax = model.read_zsmax()
            zsmax.to_netcdf(results_path.joinpath("max_water_level_map.nc"))

    def _write_geotiff(self, zsmax, demfile: Path, floodmap_fn: Path):
        # read DEM and convert units to metric units used by SFINCS

        demfile_units = self._site.attrs.dem.units
        dem_conversion = UnitfulLength(value=1.0, units=demfile_units).convert(
            UnitTypesLength("meters")
        )
        dem = dem_conversion * self._model.data_catalog.get_rasterdataset(demfile)

        # determine conversion factor for output floodmap
        floodmap_units = self._site.attrs.sfincs.floodmap_units
        floodmap_conversion = UnitfulLength(
            value=1.0, units=UnitTypesLength("meters")
        ).convert(floodmap_units)

        utils.downscale_floodmap(
            zsmax=floodmap_conversion * zsmax,
            dep=floodmap_conversion * dem,
            hmin=0.01,
            floodmap_fn=str(floodmap_fn),
        )

    def _write_sfincs_model(self, path_out: Path):
        """Write all the files for the sfincs model.

        Args:
            path_out (Path): new root of sfincs model
        """
        # Change model root to new folder
        self._model.set_root(path_out, mode="w+")

        # Write sfincs files in output folder
        self._model.write()

    def _downscale_hmax(self, zsmax, demfile: Path):
        # read DEM and convert units to metric units used by SFINCS
        demfile_units = self._site.attrs.dem.units
        dem_conversion = UnitfulLength(value=1.0, units=demfile_units).convert(
            UnitTypesLength("meters")
        )
        dem = dem_conversion * self._model.data_catalog.get_rasterdataset(demfile)

        # determine conversion factor for output floodmap
        floodmap_units = self._site.attrs.sfincs.floodmap_units
        floodmap_conversion = UnitfulLength(
            value=1.0, units=UnitTypesLength("meters")
        ).convert(floodmap_units)

        hmax = utils.downscale_floodmap(
            zsmax=floodmap_conversion * zsmax,
            dep=floodmap_conversion * dem,
            hmin=0.01,
        )
        return hmax

    def _calculate_rp_floodmaps(self):
        """Calculate flood risk maps from a set of (currently) SFINCS water level outputs using linear interpolation.

        It would be nice to make it more widely applicable and move the loading of the SFINCS results to self.postprocess_sfincs().

        generates return period water level maps in netcdf format to be used by FIAT
        generates return period water depth maps in geotiff format as product for users

        TODO: make this robust and more efficient for bigger datasets.
        """
        floodmap_rp = self._site.attrs.risk.return_periods
        result_path = self.get_result_path()
        sim_paths, offshore_sim_paths = self._get_simulation_paths()
        event_set = self._database.events.get(self._scenario.attrs.event)
        phys_proj = self._database.projections.get(self._scenario.attrs.projection)
        frequencies = event_set.attrs.frequency

        # adjust storm frequency for hurricane events
        if phys_proj.attrs.storm_frequency_increase != 0:
            storminess_increase = phys_proj.attrs.storm_frequency_increase / 100.0
            for ii, event in enumerate(self.event_list):
                if event.attrs.template == "Historical_hurricane":
                    frequencies[ii] = frequencies[ii] * (1 + storminess_increase)

        # TODO investigate why only read one model
        with SfincsAdapter(model_root=sim_paths[0]) as dummymodel:
            # read mask and bed level
            mask = dummymodel.get_mask().stack(z=("x", "y"))
            zb = dummymodel.get_bedlevel().stack(z=("x", "y")).to_numpy()

        zs_maps = []
        for simulation_path in sim_paths:
            # read zsmax data from overland sfincs model
            with SfincsAdapter(model_root=str(simulation_path)) as sim:
                zsmax = sim.read_zsmax().load()
                zs_stacked = zsmax.stack(z=("x", "y"))
                zs_maps.append(zs_stacked)

        # Create RP flood maps

        # 1a: make a table of all water levels and associated frequencies
        zs = xr.concat(zs_maps, pd.Index(frequencies, name="frequency"))
        # Get the indices of columns with all NaN values
        nan_cells = np.where(np.all(np.isnan(zs), axis=0))[0]
        # fill nan values with minimum bed levels in each grid cell, np.interp cannot ignore nan values
        zs = xr.where(np.isnan(zs), np.tile(zb, (zs.shape[0], 1)), zs)
        # Get table of frequencies
        freq = np.tile(frequencies, (zs.shape[1], 1)).transpose()

        # 1b: sort water levels in descending order and include the frequencies in the sorting process
        # (i.e. each h-value should be linked to the same p-values as in step 1a)
        sort_index = zs.argsort(axis=0)
        sorted_prob = np.flipud(np.take_along_axis(freq, sort_index, axis=0))
        sorted_zs = np.flipud(np.take_along_axis(zs.values, sort_index, axis=0))

        # 1c: Compute exceedance probabilities of water depths
        # Method: accumulate probabilities from top to bottom
        prob_exceed = np.cumsum(sorted_prob, axis=0)

        # 1d: Compute return periods of water depths
        # Method: simply take the inverse of the exceedance probability (1/Pex)
        rp_zs = 1.0 / prob_exceed

        # For each return period (T) of interest do the following:
        # For each grid cell do the following:
        # Use the table from step [1d] as a “lookup-table” to derive the T-year water depth. Use a 1-d interpolation technique:
        # h(T) = interp1 (log(T*), h*, log(T))
        # in which t* and h* are the values from the table and T is the return period (T) of interest
        # The resulting T-year water depths for all grids combined form the T-year hazard map
        rp_da = xr.DataArray(rp_zs, dims=zs.dims)

        # no_data_value = -999  # in SFINCS
        # sorted_zs = xr.where(sorted_zs == no_data_value, np.nan, sorted_zs)

        valid_cells = np.where(mask == 1)[
            0
        ]  # only loop over cells where model is not masked
        h = matlib.repmat(
            np.copy(zb), len(floodmap_rp), 1
        )  # if not flooded (i.e. not in valid_cells) revert to bed_level, read from SFINCS results so it is the minimum bed level in a grid cell

        logging.info("Calculating flood risk maps, this may take some time...")
        for jj in valid_cells:  # looping over all non-masked cells.
            # linear interpolation for all return periods to evaluate
            h[:, jj] = np.interp(
                np.log10(floodmap_rp),
                np.log10(rp_da[::-1, jj]),
                sorted_zs[::-1, jj],
                left=0,
            )

        # Re-fill locations that had nan water level for all simulations with nans
        h[:, nan_cells] = np.full(h[:, nan_cells].shape, np.nan)

        # If a cell has the same water-level as the bed elevation it should be dry (turn to nan)
        diff = h - np.tile(zb, (h.shape[0], 1))
        dry = (
            diff < 10e-10
        )  # here we use a small number instead of zero for rounding errors
        h[dry] = np.nan

        for ii, rp in enumerate(floodmap_rp):
            # #create single nc
            zs_rp_single = xr.DataArray(
                data=h[ii, :], coords={"z": zs["z"]}, attrs={"units": "meters"}
            ).unstack()
            zs_rp_single = zs_rp_single.rio.write_crs(
                zsmax.raster.crs
            )  # , inplace=True)
            zs_rp_single = zs_rp_single.to_dataset(name="risk_map")
            fn_rp = result_path.joinpath(f"RP_{rp:04d}_maps.nc")
            zs_rp_single.to_netcdf(fn_rp)

            # write geotiff
            # dem file for high resolution flood depth map
            demfile = self._database.static_path.joinpath(
                "dem", self._site.attrs.dem.filename
            )
            # writing the geotiff to the scenario results folder
            with SfincsAdapter(model_root=str(sim_paths[0])) as dummymodel:
                dummymodel._write_geotiff(
                    zs_rp_single.to_array().squeeze().transpose(),
                    demfile=demfile,
                    floodmap_fn=result_path.joinpath(f"RP_{rp:04d}_maps.tif"),
                )

    def _plot_wl_obs(self):
        """Plot water levels at SFINCS observation points as html.

        Only for single event scenarios.
        """
        for sim_path in self._get_simulation_paths():
            # read SFINCS model
            with SfincsAdapter(model_root=sim_path) as model:
                df, gdf = model._get_zs_points()

            gui_units = UnitTypesLength(self._site.attrs.gui.default_length_units)
            conversion_factor = UnitfulLength(
                value=1.0, units=UnitTypesLength("meters")
            ).convert(gui_units)

            for ii, col in enumerate(df.columns):
                # Plot actual thing
                fig = px.line(
                    df[col] * conversion_factor
                    + self._site.attrs.water_level.localdatum.height.convert(
                        gui_units
                    )  # convert to reference datum for plotting
                )

                # plot reference water levels
                fig.add_hline(
                    y=self._site.attrs.water_level.msl.height.convert(gui_units),
                    line_dash="dash",
                    line_color="#000000",
                    annotation_text="MSL",
                    annotation_position="bottom right",
                )
                if self._site.attrs.water_level.other:
                    for wl_ref in self._site.attrs.water_level.other:
                        fig.add_hline(
                            y=wl_ref.height.convert(gui_units),
                            line_dash="dash",
                            line_color="#3ec97c",
                            annotation_text=wl_ref.name,
                            annotation_position="bottom right",
                        )

                fig.update_layout(
                    autosize=False,
                    height=100 * 2,
                    width=280 * 2,
                    margin={"r": 0, "l": 0, "b": 0, "t": 20},
                    font={"size": 10, "color": "black", "family": "Arial"},
                    title={
                        "text": gdf.iloc[ii]["Description"],
                        "font": {"size": 12, "color": "black", "family": "Arial"},
                        "x": 0.5,
                        "xanchor": "center",
                    },
                    xaxis_title="Time",
                    yaxis_title=f"Water level [{gui_units}]",
                    yaxis_title_font={"size": 10, "color": "black", "family": "Arial"},
                    xaxis_title_font={"size": 10, "color": "black", "family": "Arial"},
                    showlegend=False,
                )

                # check if event is historic
                event = self._database.events.get(self._scenario.attrs.event)
                if event.attrs.timing == "historical":
                    # check if observation station has a tide gauge ID
                    # if yes to both download tide gauge data and add to plot
                    if (
                        isinstance(self._site.attrs.obs_point[ii].ID, int)
                        or self._site.attrs.obs_point[ii].file is not None
                    ):
                        if self._site.attrs.obs_point[ii].file is not None:
                            file = self._database.static_path.joinpath(
                                self._site.attrs.obs_point[ii].file
                            )
                        else:
                            file = None

                        try:
                            # TODO move download functionality to here ?
                            from flood_adapt.object_model.hazard.event.historical import (
                                HistoricalEvent,
                            )

                            df_gauge = HistoricalEvent._download_wl_data(
                                station_id=self._site.attrs.obs_point[ii].ID,
                                start_time_str=event.attrs.time.start_time,
                                stop_time_str=event.attrs.time.end_time,
                                units=UnitTypesLength(gui_units),
                                file=file,
                            )
                        except COOPSAPIError as e:
                            logging.warning(
                                f"Could not download tide gauge data for station {self._site.attrs.obs_point[ii].ID}. {e}"
                            )
                        else:
                            # If data is available, add to plot
                            fig.add_trace(
                                go.Scatter(
                                    x=pd.DatetimeIndex(df_gauge.index),
                                    y=df_gauge[1]
                                    + self._site.attrs.water_level.msl.height.convert(
                                        gui_units
                                    ),
                                    line_color="#ea6404",
                                )
                            )
                            fig["data"][0]["name"] = "model"
                            fig["data"][1]["name"] = "measurement"
                            fig.update_layout(showlegend=True)

                # write html to results folder
                station_name = gdf.iloc[ii]["Name"]
                results_path = self._get_result_path()
                fig.write_html(results_path.joinpath(f"{station_name}_timeseries.html"))
