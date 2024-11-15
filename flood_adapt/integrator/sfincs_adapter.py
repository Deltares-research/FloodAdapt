import gc
import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Union

import geopandas as gpd
import hydromt_sfincs.utils as utils
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import shapely
import xarray as xr
from cht_tide.read_bca import SfincsBoundary
from cht_tide.tide_predict import predict
from hydromt_sfincs import SfincsModel
from hydromt_sfincs.quadtree import QuadtreeGrid
from numpy import matlib

from flood_adapt.integrator.interface.hazard_adapter import IHazardAdapter
from flood_adapt.misc.config import Settings
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.object_model.hazard.event.event_set import EventSet
from flood_adapt.object_model.hazard.event.forcing.discharge import (
    DischargeConstant,
    DischargeFromCSV,
    DischargeSynthetic,
)
from flood_adapt.object_model.hazard.event.forcing.rainfall import (
    RainfallConstant,
    RainfallFromMeteo,
    RainfallSynthetic,
)
from flood_adapt.object_model.hazard.event.forcing.waterlevels import (
    WaterlevelFromCSV,
    WaterlevelFromGauged,
    WaterlevelFromModel,
    WaterlevelSynthetic,
)
from flood_adapt.object_model.hazard.event.forcing.wind import (
    WindConstant,
    WindFromMeteo,
    WindFromTrack,
    WindSynthetic,
)
from flood_adapt.object_model.hazard.event.historical import HistoricalEvent
from flood_adapt.object_model.hazard.event.hurricane import (
    HurricaneEvent,
)
from flood_adapt.object_model.hazard.event.tide_gauge import TideGauge
from flood_adapt.object_model.hazard.interface.events import IEvent, IEventModel
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingType,
    IDischarge,
    IForcing,
    IRainfall,
    IWaterlevel,
    IWind,
)
from flood_adapt.object_model.hazard.interface.models import Mode, Template, TimeModel
from flood_adapt.object_model.hazard.measure.floodwall import FloodWall
from flood_adapt.object_model.hazard.measure.green_infrastructure import (
    GreenInfrastructure,
)
from flood_adapt.object_model.hazard.measure.hazard_measure import HazardMeasure
from flood_adapt.object_model.hazard.measure.pump import Pump
from flood_adapt.object_model.hazard.physical_projection import PhysicalProjection
from flood_adapt.object_model.interface.measures import HazardType
from flood_adapt.object_model.interface.projections import PhysicalProjectionModel
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.interface.site import ISite
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulLength,
    UnitTypesDischarge,
    UnitTypesIntensity,
    UnitTypesLength,
    UnitTypesVelocity,
    UnitTypesVolume,
)
from flood_adapt.object_model.projection import Projection
from flood_adapt.object_model.site import Site
from flood_adapt.object_model.utils import cd


class SfincsAdapter(IHazardAdapter):
    _site: ISite
    _scenario: IScenario
    _model: SfincsModel

    def __init__(self, model_root: str, database=None):
        """Load overland sfincs model based on a root directory.

        Args:
            database (IDatabase): Reference to the database containing all objectmodels and site specific information.
            model_root (str): Root directory of overland sfincs model.
        """
        self._site = Site.load_file(
            Settings().database_path / "static" / "site" / "site.toml"
        )
        self._model = SfincsModel(root=model_root, mode="r")  # TODO check logger
        self._model.read()

    def __del__(self):
        """Close the log file associated with the logger and clean up file handles."""
        if hasattr(self, "_logger") and hasattr(self.logger, "handlers"):
            # Close the log file associated with the logger
            for handler in self.logger.handlers:
                handler.close()
            self.logger.handlers.clear()
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

    @property
    def has_run(self) -> bool:
        """Return True if the model has been run."""
        return self.sfincs_completed()  # + postprocessing checks

    ### HAZARD ADAPTER METHODS ###
    def read(self, path: Path):
        """Read the sfincs model from the current model root."""
        if Path(self._model.root) != Path(path):
            self._model.set_root(root=path, mode="r")
        self._model.read()

    def write(self, path_out: Union[str, os.PathLike], overwrite: bool = True):
        """Write the sfincs model configuration to a directory."""
        if not isinstance(path_out, Path):
            path_out = Path(path_out)

        if not path_out.exists():
            path_out.mkdir(parents=True)

        write_mode = "w+" if overwrite else "w"
        with cd(path_out):
            self._model.set_root(root=path_out, mode=write_mode)
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
        sim_path = sim_path or self._model.root

        with cd(sim_path):
            sfincs_log = "sfincs.log"
            with FloodAdaptLogging.to_file(file_path=sfincs_log):
                process = subprocess.run(
                    str(Settings().sfincs_path),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                self.logger.debug(process.stdout)

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
                self.logger.error(f"SFINCS model failed to run in {sim_path}.")

        return process.returncode == 0

    def run(self, scenario: IScenario):
        """Run the whole workflow (Preprocess, process and postprocess) for a given scenario."""
        try:
            self._scenario = scenario
            self.preprocess()
            self.process()
            self.postprocess()

        finally:
            self._scenario = None

    def preprocess(self):
        event: IEvent = self.database.events.get(self._scenario.attrs.event)
        sim_paths = self._get_simulation_paths()

        if isinstance(event, EventSet):
            for sub_event, sim_path in zip(event.events, sim_paths):
                self._preprocess_single_event(sub_event, output_path=sim_path)
        else:
            self._preprocess_single_event(event, output_path=sim_paths[0])

    def _preprocess_single_event(self, event: IEvent, output_path: Path):
        self.set_timing(event.attrs.time)

        # run offshore model or download wl data,
        # copy required files to the simulation folder (or folders for event sets)
        # write forcing data to event object
        event.process(self._scenario)

        for forcing in event.attrs.forcings.values():
            self.add_forcing(forcing)

        strategy = self.database.strategies.get(self._scenario.attrs.strategy)
        measures = [
            self.database.measures.get(name) for name in strategy.attrs.measures
        ]
        for measure in measures:
            self.add_measure(measure)

        self.add_projection(
            self.database.projections.get(self._scenario.attrs.projection)
        )

        # add observation points from site.toml
        self._add_obs_points()

        # write sfincs model in output destination
        self.write(path_out=output_path)

    def process(self):
        event = self.database.events.get(self._scenario.attrs.event)

        if event.attrs.mode == Mode.single_event:
            sim_path = self._get_simulation_paths()[0]
            self.execute(sim_path)

        elif event.attrs.mode == Mode.risk:
            sim_paths = self._get_simulation_paths()
            for sim_path in sim_paths:
                self.execute(sim_path)

                # postprocess subevents
                self._write_floodmap_geotiff(sim_path=sim_path)
                self._plot_wl_obs(sim_path=sim_path)
                self._write_water_level_map(sim_path=sim_path)

    def postprocess(self):
        if not self.sfincs_completed():
            raise RuntimeError("SFINCS was not run successfully!")
        event = self.database.events.get(self._scenario.attrs.event)

        if event.attrs.mode == Mode.single_event:
            self._write_floodmap_geotiff()
            self._plot_wl_obs()
            self._write_water_level_map()

        elif event.attrs.mode == Mode.risk:
            self.calculate_rp_floodmaps()

    def set_timing(self, time: TimeModel):
        """Set model reference times."""
        self._model.set_config("tref", time.start_time)
        self._model.set_config("tstart", time.start_time)
        self._model.set_config("tstop", time.end_time)

    def add_forcing(self, forcing: IForcing):
        """Get forcing data and add it to the sfincs model."""
        if forcing is None:
            return

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
                self.logger.warning(
                    f"Skipping unsupported forcing type {forcing.__class__.__name__}"
                )
                return

    def add_measure(self, measure: HazardMeasure):
        """Get measure data and add it to the sfincs model."""
        if measure is None:
            return

        match measure.attrs.type:
            case HazardType.floodwall:
                self._add_measure_floodwall(measure)
            case HazardType.greening:
                self._add_measure_greeninfra(measure)
            case HazardType.pump:
                self._add_measure_pump(measure)
            case _:
                self.logger.warning(
                    f"Skipping unsupported measure type {measure.__class__.__name__}"
                )
                return

    def add_projection(self, projection: Projection | PhysicalProjection):
        """Get forcing data currently in the sfincs model and add the projection it."""
        if not isinstance(projection, PhysicalProjection):
            projection = projection.get_physical_projection()

        if projection.attrs.sea_level_rise:
            self._model.forcing["bzs"] += projection.attrs.sea_level_rise.convert(
                "meters"
            )

        # TODO investigate how/if to add subsidence to model
        # projection.attrs.subsidence

        if projection.attrs.rainfall_multiplier:
            self.logger.info("Adding rainfall multiplier to model.")
            if "precip_2d" in self._model.forcing:
                self._model.forcing["precip_2d"] *= projection.attrs.rainfall_multiplier
            elif "precip" in self._model.forcing:
                self._model.forcing["precip"] *= projection.attrs.rainfall_multiplier
            else:
                self.logger.warning(
                    "Failed to add rainfall multiplier, no rainfall forcing found in the model."
                )

        # TODO investigate how/if to add storm frequency increase to model
        # this is only for return period calculations?
        # projection.attrs.storm_frequency_increase

    def run_completed(self) -> bool:
        """Check if the entire model run has been completed successfully by checking if all flood maps exist that are created in postprocess().

        Returns
        -------
        bool
            _description_
        """
        return (
            all(floodmap.exists() for floodmap in self._get_flood_map_paths())
            & len(self._get_flood_map_paths())
            > 0
        )

    def sfincs_completed(self, sim_path: Path = None) -> bool:
        """Check if the sfincs executable has been run successfully by checking if the output files exist in the simulation folder.

        Returns
        -------
        bool
            _description_
        """
        sim_path = sim_path or self._model.root
        SFINCS_OUTPUT_FILES = [
            Path(sim_path) / file for file in ["sfincs_his.nc", "sfincs_map.nc"]
        ]
        # Add logfile check as well from old hazard.py?
        return all(output.exists() for output in SFINCS_OUTPUT_FILES)

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

    def get_waterlevel_forcing(self, aggregate=True) -> pd.DataFrame:
        """Get the current water levels set in the model.

        Parameters
        ----------
        aggregate : bool, optional
            If True, the returned water level timeseries is the mean over all boundary points per timestep, by default True
            If False, the returned water level timeseries is defined for each boundary point per timestep.

        Returns
        -------
        pd.DataFrame
            DataFrame with datetime index called 'time', each timestep then specifies the waterlevel for each boundary point.
        """
        wl_df = self._model.forcing["bzs"].to_dataframe()["bzs"]
        if aggregate:
            wl_df = wl_df.groupby("time").mean()
        return wl_df.to_frame()

    def get_rainfall_forcing(self) -> pd.DataFrame:
        """Get the current water levels set in the model.

        Returns
        -------
        pd.DataFrame
            DataFrame with datetime index called 'time', each timestep then specifies the precipitation for the entire model or for each cell
        """
        if "precip_2d" in self._model.forcing:
            rainfall_df = self._model.forcing["precip_2d"]
        elif "precip" in self._model.forcing:
            rainfall_df = self._model.forcing["precip"]
        else:
            self.logger.warning(
                "Failed to get rainfall foring, no rainfall forcing found in the model."
            )
            return
        return rainfall_df.to_frame()

    ### PRIVATE METHODS - Should not be called from outside of this class ###

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
        t0, t1 = self._model.get_model_time()
        if isinstance(forcing, WindConstant):
            self._model.setup_wind_forcing(
                timeseries=None,
                magnitude=forcing.speed.convert(UnitTypesVelocity.mps),
                direction=forcing.direction.value,
            )
        elif isinstance(forcing, WindSynthetic):
            tmp_path = Path(tempfile.gettempdir()) / "wind.csv"
            forcing.get_data(t0=t0, t1=t1).to_csv(tmp_path)
            self._model.setup_wind_forcing(
                timeseries=tmp_path, magnitude=None, direction=None
            )
        elif isinstance(forcing, WindFromMeteo):
            ds = forcing.get_data(t0, t1)

            if ds["lon"].min() > 180:
                ds["lon"] = ds["lon"] - 360

            self._set_wind_forcing(ds)
        elif isinstance(forcing, WindFromTrack):
            self._set_config_spw(forcing.path)
        else:
            self.logger.warning(
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
        t0, t1 = self._model.get_model_time()
        if isinstance(forcing, RainfallConstant):
            self._model.setup_precip_forcing(
                timeseries=None,
                magnitude=forcing.intensity.convert(UnitTypesIntensity.mm_hr),
            )
        elif isinstance(forcing, RainfallSynthetic):
            tmp_path = Path(tempfile.gettempdir()) / "precip.csv"
            forcing.get_data(t0=t0, t1=t1).to_csv(tmp_path)
            self._model.setup_precip_forcing(timeseries=tmp_path)
        elif isinstance(forcing, RainfallFromMeteo):
            ds = forcing.get_data(t0=t0, t1=t1)

            if ds["lon"].min() > 180:
                ds["lon"] = ds["lon"] - 360

            self._model.setup_precip_forcing_from_grid(
                precip=ds["precip"], aggregate=False
            )
        else:
            self.logger.warning(
                f"Unsupported rainfall forcing type: {forcing.__class__.__name__}"
            )
            return

    def _add_forcing_discharge(self, forcing: IDischarge):
        """Add spatially constant discharge forcing to sfincs model. Use timeseries or a constant magnitude.

        Parameters
        ----------
        forcing : IDischarge
            The discharge forcing to add to the model.
            Can be a constant, synthetic or from a csv file.
            Also contains the river information.
        """
        if isinstance(
            forcing, (DischargeConstant, DischargeFromCSV, DischargeSynthetic)
        ):
            self._set_single_river_forcing(discharge=forcing)
        else:
            self.logger.warning(
                f"Unsupported discharge forcing type: {forcing.__class__.__name__}"
            )

    def _add_forcing_waterlevels(self, forcing: IWaterlevel):
        t0, t1 = self._model.get_model_time()
        if isinstance(
            forcing, (WaterlevelSynthetic, WaterlevelFromCSV, WaterlevelFromGauged)
        ):
            self._set_waterlevel_forcing(forcing.get_data(t0, t1))
        elif isinstance(forcing, WaterlevelFromModel):
            self._set_waterlevel_forcing(forcing.get_data(t0, t1))
            self._turn_off_bnd_press_correction()
        else:
            self.logger.warning(
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
        polygon_file = (
            self.database.measures.input_path
            / floodwall.attrs.name
            / floodwall.attrs.polygon_file
        )
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
                        units=self.database.site.attrs.gui.default_length_units,
                    ).convert(UnitTypesLength("meters"))
                )
                for height in gdf_floodwall["z"]
            ]
            gdf_floodwall["z"] = heights
            self.logger.info("Using floodwall height from shape file.")
        except Exception:
            self.logger.warning(
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
            polygon_file = (
                self.database.measures.input_path
                / green_infrastructure.attrs.name
                / green_infrastructure.attrs.polygon_file
            )
        elif green_infrastructure.attrs.selection_type == "aggregation_area":
            # TODO this logic already exists in the Database controller but cannot be used due to cyclic imports
            # Loop through available aggregation area types
            for aggr_dict in self.database.site.attrs.fiat.aggregation:
                # check which one is used in measure
                if (
                    not aggr_dict.name
                    == green_infrastructure.attrs.aggregation_area_type
                ):
                    continue
                # load geodataframe
                aggr_areas = gpd.read_file(
                    self.database.static_path / "site" / aggr_dict.file,
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
        polygon_file = (
            self.database.measures.input_path
            / pump.attrs.name
            / pump.attrs.polygon_file
        )
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

    ### SFINCS SETTERS ###
    def _set_waterlevel_forcing(self, df_ts: pd.DataFrame):
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
            name = df_ts.columns[0]
            for i in range(1, len(gdf_locs)):
                df_ts[i + 1] = df_ts[name]
            df_ts.columns = range(1, len(gdf_locs) + 1)

        # HydroMT function: set waterlevel forcing from time series
        self._model.set_forcing_1d(
            name="bzs", df_ts=df_ts, gdf_locs=gdf_locs, merge=False
        )

    def _set_rainfall_forcing(
        self, timeseries: Union[str, os.PathLike] = None, const_precip: float = None
    ):
        """Add spatially uniform precipitation to sfincs model.

        Parameters
        ----------
        precip : Union[str, os.PathLike], optional
            timeseries file of precipitation (.csv) which has two columns: time and precipitation, by default None
        const_precip : float, optional
            time-invariant precipitation magnitude [mm_hr], by default None
        """
        self._model.setup_precip_forcing(timeseries=timeseries, magnitude=const_precip)

    def _set_single_river_forcing(self, discharge: IDischarge):
        """Add discharge to overland sfincs model.

        Parameters
        ----------
        discharge : IDischarge
            Discharge object with discharge timeseries data and river information.
        """
        if not isinstance(
            discharge, (DischargeConstant, DischargeSynthetic, DischargeFromCSV)
        ):
            self.logger.warning(
                f"Unsupported discharge forcing type: {discharge.__class__.__name__}"
            )
            return

        self.logger.info(f"Setting discharge forcing for river: {discharge.river.name}")
        t0, t1 = self._model.get_model_time()
        model_rivers = self._model.forcing["dis"].vector.to_gdf()

        # Check that the river is defined in the model and that the coordinates match
        river_loc = shapely.Point(
            discharge.river.x_coordinate, discharge.river.y_coordinate
        )
        tolerance = 0.001  # in degrees, ~111 meters at the equator. (0.0001: 11 meters at the equator)
        river_gdf = model_rivers[model_rivers.distance(river_loc) <= tolerance]
        river_inds = river_gdf.index.to_list()
        if len(river_inds) != 1:
            raise ValueError(
                f"River {discharge.river.name} is not defined in the sfincs model. Please ensure the river coordinates in the site.toml match the coordinates for rivers in the SFINCS model."
            )

        # Create a geodataframe with the river coordinates, the timeseries data and rename the column to the river index defined in the model
        df = discharge.get_data(t0, t1)
        df = df.rename(columns={df.columns[0]: river_inds[0]})

        # HydroMT function: set discharge forcing from time series and river coordinates
        self._model.setup_discharge_forcing(
            locations=river_gdf,
            timeseries=df,
            merge=True,
        )

    def _set_wind_forcing(self, ds: xr.DataArray):
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
        if self.database.site.attrs.obs_point is not None:
            self.logger.info("Adding observation points to the overland flood model...")

            obs_points = self.database.site.attrs.obs_point
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

    def _add_bzs_from_bca(
        self, event: IEventModel, physical_projection: PhysicalProjectionModel
    ):
        # ONLY offshore models
        """Convert tidal constituents from bca file to waterlevel timeseries that can be read in by hydromt_sfincs."""
        sb = SfincsBoundary()
        sb.read_flow_boundary_points(Path(self._model.root) / "sfincs.bnd")
        sb.read_astro_boundary_conditions(Path(self._model.root) / "sfincs.bca")

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

    def _add_forcing_spw(
        self,
        historical_hurricane: HurricaneEvent,
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
        spw_file = historical_hurricane.make_spw_file(
            cyc_file=self.database.events.input_path
            / historical_hurricane.attrs.name
            / f"{historical_hurricane.attrs.track_name}.cyc",
            output_dir=model_dir,
        )
        # TODO check with @gundula
        self._set_config_spw(spw_file.name)

    ### PRIVATE GETTERS ###
    def _get_result_path(self, scenario_name: str = None) -> Path:
        """Return the path to store the results.

        Order of operations:
        - try to return the path from given argument scenario_name
        - try to return the path from self._scenario
        - return the path from self._model.root
        """
        if scenario_name is None:
            if hasattr(self, "_scenario"):
                scenario_name = self._scenario.attrs.name
            else:
                scenario_name = self._model.root

        return self.database.scenarios.output_path / scenario_name / "Flooding"

    def _get_simulation_paths(self) -> List[Path]:
        event = self.database.events.get(self._scenario.attrs.event)
        base_path = (
            self._get_result_path()
            / "simulations"
            / self.database.site.attrs.sfincs.overland_model
        )

        if event.attrs.mode == Mode.single_event:
            return [base_path]
        elif event.attrs.mode == Mode.risk:
            return [
                base_path.parent / sub_event.attrs.name / base_path.name
                for sub_event in event.events
            ]
        else:
            raise ValueError(f"Unsupported mode: {event.attrs.mode}")

    def _get_simulation_path_offshore(self) -> List[Path]:
        # Get the path to the offshore model (will not be used if offshore model is not created)
        event = self.database.events.get(self._scenario.attrs.event)
        base_path = (
            self._get_result_path()
            / "simulations"
            / self.database.site.attrs.sfincs.offshore_model
        )

        if event.attrs.mode == Mode.single_event:
            return [base_path]
        elif event.attrs.mode == Mode.risk:
            return [
                base_path.parent / sub_event.attrs.name / base_path.name
                for sub_event in event.events
            ]
        else:
            raise ValueError(f"Unsupported mode: {event.attrs.mode}")

    def _get_flood_map_paths(self) -> list[Path]:
        """_summary_."""
        results_path = self._get_result_path()
        mode = self.database.events.get(self._scenario.attrs.event).attrs.mode

        if mode == Mode.single_event:
            map_fn = [results_path / "max_water_level_map.nc"]

        elif mode == Mode.risk:
            map_fn = []
            for rp in self.database.site.attrs.risk.return_periods:
                map_fn.append(results_path / f"RP_{rp:04d}_maps.nc")
        else:
            raise ValueError(f"Unsupported mode: {mode}")

        return map_fn

    def _get_wl_df_from_offshore_his_results(self) -> pd.DataFrame:
        """Create a pd.Dataframe with waterlevels from the offshore model at the bnd locations of the overland model.

        Returns
        -------
        wl_df: pd.DataFrame
            time series of water level.
        """
        ds_his = utils.read_sfincs_his_results(
            Path(self._model.root) / "sfincs_his.nc",
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

        names = []
        descriptions = []
        # get station names from site.toml
        if self.database.site.attrs.obs_point is not None:
            obs_points = self.database.site.attrs.obs_point
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
    def _write_floodmap_geotiff(self, sim_path: Path = None):
        results_path = self._get_result_path()
        sim_path = sim_path or self._get_simulation_paths()[0]

        # read SFINCS model
        with SfincsAdapter(model_root=sim_path) as model:
            # dem file for high resolution flood depth map
            demfile = (
                self.database.static_path
                / "dem"
                / self.database.site.attrs.dem.filename
            )

            # read max. water level
            zsmax = model._get_zsmax()

            # writing the geotiff to the scenario results folder
            model._write_geotiff(
                zsmax,
                demfile=demfile,
                floodmap_fn=results_path / f"FloodMap_{self._scenario.attrs.name}.tif",
            )

    def _write_water_level_map(self, sim_path: Path = None):
        """Read simulation results from SFINCS and saves a netcdf with the maximum water levels."""
        results_path = self._get_result_path()
        sim_paths = [sim_path] if sim_path else self._get_simulation_paths()
        # Why only 1 model?
        with SfincsAdapter(model_root=sim_paths[0]) as model:
            zsmax = model._get_zsmax()
            zsmax.to_netcdf(results_path / "max_water_level_map.nc")

    def _write_geotiff(self, zsmax, demfile: Path, floodmap_fn: Path):
        # read DEM and convert units to metric units used by SFINCS

        demfile_units = self.database.site.attrs.dem.units
        dem_conversion = UnitfulLength(value=1.0, units=demfile_units).convert(
            UnitTypesLength("meters")
        )
        dem = dem_conversion * self._model.data_catalog.get_rasterdataset(demfile)

        # determine conversion factor for output floodmap
        floodmap_units = self.database.site.attrs.sfincs.floodmap_units
        floodmap_conversion = UnitfulLength(
            value=1.0, units=UnitTypesLength("meters")
        ).convert(floodmap_units)

        utils.downscale_floodmap(
            zsmax=floodmap_conversion * zsmax,
            dep=floodmap_conversion * dem,
            hmin=0.01,
            floodmap_fn=str(floodmap_fn),
        )

    def _downscale_hmax(self, zsmax, demfile: Path):
        # read DEM and convert units to metric units used by SFINCS
        demfile_units = self.database.site.attrs.dem.units
        dem_conversion = UnitfulLength(value=1.0, units=demfile_units).convert(
            UnitTypesLength("meters")
        )
        dem = dem_conversion * self._model.data_catalog.get_rasterdataset(demfile)

        # determine conversion factor for output floodmap
        floodmap_units = self.database.site.attrs.sfincs.floodmap_units
        floodmap_conversion = UnitfulLength(
            value=1.0, units=UnitTypesLength("meters")
        ).convert(floodmap_units)

        hmax = utils.downscale_floodmap(
            zsmax=floodmap_conversion * zsmax,
            dep=floodmap_conversion * dem,
            hmin=0.01,
        )
        return hmax

    def _plot_wl_obs(self, sim_path: Path = None):
        """Plot water levels at SFINCS observation points as html.

        Only for single event scenarios, or for a specific simulation path containing the written and processed sfincs model.
        """
        event = self.database.events.get(self._scenario.attrs.event)
        if sim_path is None:
            if event.attrs.mode != Mode.single_event:
                raise ValueError(
                    "This function is only available for single event scenarios."
                )

        sim_path = sim_path or self._get_simulation_paths()[0]
        # read SFINCS model
        with SfincsAdapter(model_root=sim_path) as model:
            df, gdf = model._get_zs_points()

        gui_units = UnitTypesLength(self.database.site.attrs.gui.default_length_units)
        conversion_factor = UnitfulLength(
            value=1.0, units=UnitTypesLength("meters")
        ).convert(gui_units)

        for ii, col in enumerate(df.columns):
            # Plot actual thing
            fig = px.line(
                df[col] * conversion_factor
                + self.database.site.attrs.water_level.localdatum.height.convert(
                    gui_units
                )  # convert to reference datum for plotting
            )

            # plot reference water levels
            fig.add_hline(
                y=self.database.site.attrs.water_level.msl.height.convert(gui_units),
                line_dash="dash",
                line_color="#000000",
                annotation_text="MSL",
                annotation_position="bottom right",
            )
            if self.database.site.attrs.water_level.other:
                for wl_ref in self.database.site.attrs.water_level.other:
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
            if isinstance(event, HistoricalEvent):
                if self._site.attrs.tide_gauge is None:
                    continue
                df_gauge = TideGauge(
                    attrs=self._site.attrs.tide_gauge
                ).get_waterlevels_in_time_frame(
                    time=TimeModel(
                        start_time=event.attrs.time.start_time,
                        end_time=event.attrs.time.end_time,
                    ),
                    units=UnitTypesLength(gui_units),
                )

                if df_gauge is not None:
                    waterlevel = df_gauge.iloc[
                        :, 0
                    ] + self.database.site.attrs.water_level.msl.height.convert(
                        gui_units
                    )

                    # If data is available, add to plot
                    fig.add_trace(
                        go.Scatter(
                            x=pd.DatetimeIndex(df_gauge.index),
                            y=waterlevel,
                            line_color="#ea6404",
                        )
                    )
                    fig["data"][0]["name"] = "model"
                    fig["data"][1]["name"] = "measurement"
                    fig.update_layout(showlegend=True)

            # write html to results folder
            station_name = gdf.iloc[ii]["Name"]
            results_path = self._get_result_path()
            fig.write_html(results_path / f"{station_name}_timeseries.html")

    ## RISK EVENTS ##
    def calculate_rp_floodmaps(self):
        """Calculate flood risk maps from a set of (currently) SFINCS water level outputs using linear interpolation.

        It would be nice to make it more widely applicable and move the loading of the SFINCS results to self.postprocess_sfincs().

        generates return period water level maps in netcdf format to be used by FIAT
        generates return period water depth maps in geotiff format as product for users

        TODO: make this robust and more efficient for bigger datasets.
        """
        eventset = self.database.events.get(self._scenario.attrs.event)
        if eventset.attrs.mode != Mode.risk:
            raise ValueError("This function is only available for risk scenarios.")

        result_path = self._get_result_path()
        sim_paths = self._get_simulation_paths()

        phys_proj: PhysicalProjection = self.database.projections.get(
            self._scenario.attrs.projection
        ).get_physical_projection()
        floodmap_rp = self.database.site.attrs.risk.return_periods
        frequencies = eventset.attrs.frequency

        # adjust storm frequency for hurricane events
        if phys_proj.attrs.storm_frequency_increase != 0:
            storminess_increase = phys_proj.attrs.storm_frequency_increase / 100.0
            for ii, event in enumerate(eventset.events):
                if event.attrs.template == Template.Hurricane:
                    frequencies[ii] = frequencies[ii] * (1 + storminess_increase)

        with SfincsAdapter(model_root=sim_paths[0]) as dummymodel:
            # read mask and bed level
            mask = dummymodel.get_mask().stack(z=("x", "y"))
            zb = dummymodel.get_bedlevel().stack(z=("x", "y")).to_numpy()

        zs_maps = []
        for simulation_path in sim_paths:
            # read zsmax data from overland sfincs model
            with SfincsAdapter(model_root=str(simulation_path)) as sim:
                zsmax = sim._get_zsmax().load()
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

        self.logger.info("Calculating flood risk maps, this may take some time...")
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
            fn_rp = result_path / f"RP_{rp:04d}_maps.nc"
            zs_rp_single.to_netcdf(fn_rp)

            # write geotiff
            # dem file for high resolution flood depth map
            demfile = (
                self.database.static_path
                / "dem"
                / self.database.site.attrs.dem.filename
            )
            # writing the geotiff to the scenario results folder
            with SfincsAdapter(model_root=str(sim_paths[0])) as dummymodel:
                dummymodel._write_geotiff(
                    zs_rp_single.to_array().squeeze().transpose(),
                    demfile=demfile,
                    floodmap_fn=result_path / f"RP_{rp:04d}_maps.tif",
                )
