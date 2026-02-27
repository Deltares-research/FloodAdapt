import gc
import logging
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Union

import contextily as ctx
import geopandas as gpd
import hydromt_sfincs.utils as utils
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import pyproj
import shapely
import xarray as xr
import xugrid as xu
from cht_cyclones.tropical_cyclone import TropicalCyclone
from cht_tide.read_bca import SfincsBoundary
from cht_tide.tide_predict import predict
from hydromt_sfincs import SfincsModel as HydromtSfincsModel
from hydromt_sfincs.quadtree import QuadtreeGrid

# import cartopy.crs as ccrs
from matplotlib import animation
from shapely.affinity import translate

from flood_adapt.adapter.interface.hazard_adapter import IHazardAdapter
from flood_adapt.config.settings import Settings
from flood_adapt.config.site import Site
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.misc.path_builder import (
    ObjectDir,
    TopLevelDir,
    db_path,
)
from flood_adapt.misc.utils import cd, resolve_filepath
from flood_adapt.objects.events.event_set import EventSet
from flood_adapt.objects.events.events import Event, Mode, Template
from flood_adapt.objects.events.hurricane import TranslationModel
from flood_adapt.objects.events.synthetic import SyntheticEvent
from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.forcing.discharge import (
    DischargeConstant,
    DischargeCSV,
    DischargeSynthetic,
)
from flood_adapt.objects.forcing.forcing import (
    ForcingSource,
    ForcingType,
    IDischarge,
    IForcing,
    IRainfall,
    IWaterlevel,
    IWind,
)
from flood_adapt.objects.forcing.meteo_handler import MeteoHandler
from flood_adapt.objects.forcing.rainfall import (
    RainfallConstant,
    RainfallCSV,
    RainfallMeteo,
    RainfallNetCDF,
    RainfallSynthetic,
    RainfallTrack,
)
from flood_adapt.objects.forcing.time_frame import TimeFrame
from flood_adapt.objects.forcing.unit_system import VerticalReference
from flood_adapt.objects.forcing.waterlevels import (
    WaterlevelCSV,
    WaterlevelGauged,
    WaterlevelModel,
    WaterlevelSynthetic,
)
from flood_adapt.objects.forcing.wind import (
    WindConstant,
    WindCSV,
    WindMeteo,
    WindNetCDF,
    WindSynthetic,
    WindTrack,
)
from flood_adapt.objects.measures.measures import (
    FloodWall,
    GreenInfrastructure,
    Measure,
    Pump,
)
from flood_adapt.objects.projections.projections import (
    PhysicalProjection,
    Projection,
)
from flood_adapt.objects.scenarios.scenarios import Scenario
from flood_adapt.workflows.floodwall import create_z_linestrings_from_bfe

logger = FloodAdaptLogging.getLogger("SfincsAdapter")


class SfincsAdapter(IHazardAdapter):
    """Adapter for the SFINCS model.

    This class is used to run the SFINCS model and process the results.

    Attributes
    ----------
    settings : SfincsModel
        The settings for the SFINCS model.
    """

    _site: Site
    _model: HydromtSfincsModel

    ###############
    ### PUBLIC ####
    ###############

    ### HAZARD ADAPTER METHODS ###
    def __init__(self, model_root: Path):
        """Load overland sfincs model based on a root directory.

        Parameters
        ----------
        model_root : Path
            Root directory of overland sfincs model.
        """
        self.settings = self.database.site.sfincs
        self.units = self.database.site.gui.units
        self._model = HydromtSfincsModel(
            root=model_root.resolve().as_posix(),
            mode="r",
            logger=self._setup_sfincs_logger(model_root),
        )
        self._model.read()

    def read(self, path: Path):
        """Read the sfincs model from the current model root."""
        if Path(self._model.root).resolve() != Path(path).resolve():
            self._model.set_root(root=path.as_posix(), mode="r")
        self._model.read()

    def write(self, path_out: Union[str, os.PathLike], overwrite: bool = True):
        """Write the sfincs model configuration to a directory."""
        root = self.get_model_root()
        if not isinstance(path_out, Path):
            path_out = Path(path_out).resolve()

        if not path_out.exists():
            path_out.mkdir(parents=True)

        if root != path_out:
            shutil.copytree(root, path_out, dirs_exist_ok=True)

        write_mode = "w+" if overwrite else "w"
        with cd(path_out):
            self._model.set_root(root=path_out.as_posix(), mode=write_mode)
            self._model.write()

    def close_files(self):
        """Close all open files and clean up file handles."""
        for _logger in [logger, self.sfincs_logger]:
            if hasattr(_logger, "handlers"):
                for handler in _logger.handlers:
                    if isinstance(handler, logging.FileHandler):
                        handler.close()
                        _logger.removeHandler(handler)

    def __enter__(self) -> "SfincsAdapter":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        self.close_files()
        return False

    def has_run(self, scenario: Scenario) -> bool:
        """Check if the model has been run."""
        return self.run_completed(scenario)

    def execute(self, path: Path, strict: bool = True) -> bool:
        """
        Run the sfincs executable in the specified path.

        Parameters
        ----------
        path : str
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
        sfincs_bin = Settings().sfincs_bin_path
        if not sfincs_bin or not sfincs_bin.exists():
            raise FileNotFoundError(
                f"SFINCS binary not found at {sfincs_bin}. Please check your settings."
            )

        with cd(path):
            logger.info(f"Running SFINCS in {path}")
            process = subprocess.run(
                sfincs_bin.as_posix(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.sfincs_logger.info(process.stdout)
            logger.debug(process.stdout)

        self._cleanup_simulation_folder(path)

        if process.returncode != 0:
            if Settings().delete_crashed_runs:
                # Remove all files in the simulation folder except for the log files
                for subdir, dirs, files in os.walk(path, topdown=False):
                    for file in files:
                        if not file.endswith(".log"):
                            os.remove(os.path.join(subdir, file))

                    if not os.listdir(subdir):
                        shutil.rmtree(subdir, ignore_errors=True)

            if strict:
                raise RuntimeError(f"SFINCS model failed to run in {path}.")
            else:
                logger.error(f"SFINCS model failed to run in {path}.")

        return process.returncode == 0

    def run(self, scenario: Scenario):
        """Run the whole workflow (Preprocess, process and postprocess) for a given scenario."""
        self._ensure_no_existing_forcings()
        event = self.database.events.get(scenario.event)

        if event.mode == Mode.risk:
            self._run_risk_scenario(scenario=scenario)
        else:
            self._run_single_event(scenario=scenario, event=event)

    def preprocess(self, scenario: Scenario, event: Event):
        """
        Preprocess the SFINCS model for a given scenario.

        Parameters
        ----------
        scenario : Scenario
            Scenario to preprocess.
        event : Event, optional
            Event to preprocess, by default None.
        """
        # I dont like this due to it being state based and might break if people use functions in the wrong order
        # Currently only used to pass projection + event stuff to WaterlevelModel

        sim_path = self._get_simulation_path(scenario=scenario, sub_event=event)
        sim_path.mkdir(parents=True, exist_ok=True)
        template_path = (
            self.database.static.get_overland_sfincs_model().get_model_root()
        )

        with SfincsAdapter(model_root=template_path) as model:
            model._load_scenario_objects(scenario, event)
            is_risk = "Probabilistic " if model._event_set is not None else ""
            logger.info(
                f"Preprocessing Scenario `{model._scenario.name}`: {is_risk}Event `{model._event.name}`, Strategy `{model._strategy.name}`, Projection `{model._projection.name}`"
            )
            # Write template model to output path and set it as the model root so focings can write to it
            model.set_timing(model._event.time)
            model.write(sim_path)

            # Event
            for forcing in model._event.get_forcings():
                model.add_forcing(forcing)

            if model.rainfall is not None:
                logger.info(
                    f"Adding event's rainfall multiplier: {model._event.rainfall_multiplier}"
                )
                model.rainfall *= model._event.rainfall_multiplier

            # Measures
            for measure in model._strategy.get_hazard_measures():
                model.add_measure(measure)

            # Projection
            model.add_projection(model._projection)

            # Output
            model.add_obs_points()

            # Save any changes made to disk as well
            model.write(path_out=sim_path)

    def process(self, scenario: Scenario, event: Event):
        if event.mode != Mode.single_event:
            raise ValueError(f"Unsupported event mode: {event.mode}.")

        sim_path = self._get_simulation_path(scenario=scenario, sub_event=event)
        logger.info(f"Running SFINCS for single event Scenario `{scenario.name}`")
        self.execute(sim_path)

    def postprocess(self, scenario: Scenario, event: Event):
        if event.mode != Mode.single_event:
            raise ValueError(f"Unsupported event mode: {event.mode}.")

        logger.info(f"Postprocessing SFINCS for Scenario `{scenario.name}`")
        if not self.sfincs_completed(
            self._get_simulation_path(scenario, sub_event=event)
        ):
            raise RuntimeError("SFINCS was not run successfully!")

        self.write_water_level_map(scenario)
        self.write_floodmap_geotiff(scenario)
        self.plot_wl_obs(scenario)

    def set_timing(self, time: TimeFrame):
        """Set model reference times."""
        logger.info(f"Setting timing for the SFINCS model: `{time}`")
        self._model.set_config("tref", time.start_time)
        self._model.set_config("tstart", time.start_time)
        self._model.set_config("tstop", time.end_time)

    def add_forcing(self, forcing: IForcing):
        """Get forcing data and add it."""
        if forcing is None:
            return

        logger.info(
            f"Adding {forcing.type.capitalize()}: {forcing.source.capitalize()}"
        )
        if isinstance(forcing, IRainfall):
            self._add_forcing_rain(forcing)
        elif isinstance(forcing, IWind):
            self._add_forcing_wind(forcing)
        elif isinstance(forcing, IDischarge):
            self._add_forcing_discharge(forcing)
        elif isinstance(forcing, IWaterlevel):
            self._add_forcing_waterlevels(forcing)
        else:
            logger.warning(
                f"Skipping unsupported forcing type {forcing.__class__.__name__}"
            )

    def add_measure(self, measure: Measure):
        """Get measure data and add it."""
        logger.info(
            f"Adding {measure.__class__.__name__.capitalize()} `{measure.name}`"
        )

        if isinstance(measure, FloodWall):
            self._add_measure_floodwall(measure)
        elif isinstance(measure, GreenInfrastructure):
            self._add_measure_greeninfra(measure)
        elif isinstance(measure, Pump):
            self._add_measure_pump(measure)
        else:
            logger.warning(
                f"Skipping unsupported measure type {measure.__class__.__name__}"
            )

    def add_projection(self, projection: Projection):
        """Get forcing data currently in the sfincs model and add the projection it."""
        logger.info(f"Adding Projection `{projection.name}`")
        phys_projection = projection.physical_projection

        if phys_projection.sea_level_rise:
            if self.waterlevels is not None:
                logger.info(
                    f"Adding projected sea level rise `{phys_projection.sea_level_rise}`"
                )
                self.waterlevels += phys_projection.sea_level_rise.convert(
                    us.UnitTypesLength.meters
                )

        if phys_projection.rainfall_multiplier:
            if self.rainfall is not None:
                logger.info(
                    f"Adding projected rainfall multiplier `{phys_projection.rainfall_multiplier}`"
                )
                self.rainfall *= phys_projection.rainfall_multiplier

    ### GETTERS ###
    def get_model_time(self) -> TimeFrame:
        t0, t1 = self._model.get_model_time()
        return TimeFrame(start_time=t0, end_time=t1)

    def get_model_root(self) -> Path:
        return Path(self._model.root)

    def get_mask(self) -> xr.DataArray:
        """Get mask with inactive cells from model."""
        mask = self._model.mask
        return mask

    def get_bedlevel(self) -> xr.DataArray:
        """Get bed level from model."""
        self._model.read_results()
        zb = self._model.results["zb"]
        # Convert bed level from meters to floodmap units
        conversion = us.UnitfulLength(
            value=1.0, units=us.UnitTypesLength.meters
        ).convert(self.settings.config.floodmap_units)
        zb = zb * conversion
        zb.attrs["units"] = self.settings.config.floodmap_units.value
        return zb

    def get_model_boundary(self) -> gpd.GeoDataFrame:
        """Get bounding box from model."""
        boundary = self._model.region[["geometry"]]
        return boundary

    def get_model_grid(self) -> QuadtreeGrid:
        """Get grid from model.

        Returns
        -------
        QuadtreeGrid
            QuadtreeGrid with the model grid
        """
        return self._model.quadtree

    def get_finest_res(self) -> float:
        """Get the finest resolution of the model grid."""
        if self._model.grid_type == "quadtree":
            res0 = self._model.quadtree.dx
            res = res0 / 2**self._model.quadtree.nr_refinement_levels
        else:
            res = self._model.res[0]
        return res

    # Forcing properties
    @property
    def waterlevels(self) -> xr.Dataset | xr.DataArray | None:
        return self._model.forcing.get("bzs")

    @waterlevels.setter
    def waterlevels(self, waterlevels: xr.Dataset | xr.DataArray):
        if self.waterlevels is None or self.waterlevels.size == 0:
            raise ValueError("No water level forcing found in the model.")
        self._model.forcing["bzs"] = waterlevels

    @property
    def discharge(self) -> xr.Dataset | xr.DataArray | None:
        return self._model.forcing.get("dis")

    @discharge.setter
    def discharge(self, discharge: xr.Dataset | xr.DataArray):
        if self.discharge is None or self.discharge.size == 0:
            raise ValueError("No discharge forcing found in the model.")
        self._model.forcing["dis"] = discharge

    @property
    def rainfall(self) -> xr.Dataset | xr.DataArray | None:
        names = ["precip", "precip_2d"]
        in_model = [name for name in names if name in self._model.forcing]
        if len(in_model) == 0:
            return None
        elif len(in_model) == 1:
            return self._model.forcing[in_model[0]]
        else:
            raise ValueError("Multiple rainfall forcings found in the model.")

    @rainfall.setter
    def rainfall(self, rainfall: xr.Dataset | xr.DataArray):
        if self.rainfall is None or self.rainfall.size == 0:
            raise ValueError("No rainfall forcing found in the model.")
        elif "precip_2d" in self._model.forcing:
            self._model.forcing["precip_2d"] = rainfall
        elif "precip" in self._model.forcing:
            self._model.forcing["precip"] = rainfall
        else:
            raise ValueError("Unsupported rainfall forcing in the model.")

    @property
    def wind(self) -> xr.Dataset | xr.DataArray | None:
        wind_names = ["wnd", "wind_2d", "wind", "wind10_u", "wind10_v"]
        wind_in_model = [name for name in wind_names if name in self._model.forcing]
        if len(wind_in_model) == 0:
            return None
        elif len(wind_in_model) == 1:
            return self._model.forcing[wind_in_model[0]]
        elif len(wind_in_model) == 2:
            if not ("wind10_u" in wind_in_model and "wind10_v" in wind_in_model):
                raise ValueError(
                    "Multiple wind forcings found in the model. Both should be wind10_u and wind10_v or a singular wind forcing."
                )
            return xr.Dataset(
                {
                    "wind10_u": self._model.forcing["wind10_u"],
                    "wind10_v": self._model.forcing["wind10_v"],
                }
            )
        else:
            raise ValueError("Multiple wind forcings found in the model.")

    @wind.setter
    def wind(self, wind: xr.Dataset | xr.DataArray):
        if (not self.wind) or (self.wind.size == 0):
            raise ValueError("No wind forcing found in the model.")

        elif "wind_2d" in self._model.forcing:
            self._model.forcing["wind_2d"] = wind
        elif "wind" in self._model.forcing:
            self._model.forcing["wind"] = wind
        elif "wnd" in self._model.forcing:
            self._model.forcing["wnd"] = wind
        elif "wind10_u" in self._model.forcing and "wind10_v" in self._model.forcing:
            self._model.forcing["wind10_u"] = wind["wind10_u"]
            self._model.forcing["wind10_v"] = wind["wind10_v"]
        else:
            raise ValueError("Unsupported wind forcing in the model.")

    ### OUTPUT ###
    def run_completed(self, scenario: Scenario) -> bool:
        """Check if the entire model run has been completed successfully by checking if all flood maps exist that are created in postprocess().

        Returns
        -------
        bool : True if all flood maps exist, False otherwise.

        """
        paths = self._get_flood_map_paths(scenario)
        any_floodmap = len(paths) > 0
        all_exist = all(floodmap.exists() for floodmap in paths)
        return any_floodmap and all_exist

    def sfincs_completed(self, sim_path: Path) -> bool:
        """Check if the sfincs executable has been run successfully by checking if the output files exist in the simulation folder.

        Parameters
        ----------
        sim_path : Path
            Path to the simulation folder to check.

        Returns
        -------
        bool: True if the sfincs executable has been run successfully, False otherwise.

        """
        SFINCS_OUTPUT_FILES = ["sfincs_map.nc"]

        if self.settings.obs_point is not None:
            SFINCS_OUTPUT_FILES.append("sfincs_his.nc")

        to_check = [Path(sim_path) / file for file in SFINCS_OUTPUT_FILES]
        return all(output.exists() for output in to_check)

    def write_floodmap_geotiff(
        self, scenario: Scenario, sim_path: Optional[Path] = None
    ):
        """
        Read simulation results from SFINCS and saves a geotiff with the maximum water levels.

        Produced floodmap is in the units defined in the sfincs config settings.

        Parameters
        ----------
        scenario : Scenario
            Scenario for which to create the floodmap.
        sim_path : Path, optional
            Path to the simulation folder, by default None.
        """
        logger.info("Writing flood maps to geotiff.")
        results_path = self._get_result_path(scenario)
        sim_path = sim_path or self._get_simulation_path(scenario)
        demfile = self.database.get_topobathy_path()

        with SfincsAdapter(model_root=sim_path) as model:
            zsmax = model._get_zsmax()

            dem = model._model.data_catalog.get_rasterdataset(demfile)

            # convert dem from dem units to floodmap units
            dem_conversion = us.UnitfulLength(
                value=1.0, units=self.settings.dem.units
            ).convert(self.settings.config.floodmap_units)

            floodmap_fn = results_path / f"FloodMap_{scenario.name}.tif"

            utils.downscale_floodmap(
                zsmax=zsmax,
                dep=dem_conversion * dem,
                hmin=0.01,
                floodmap_fn=floodmap_fn.as_posix(),
            )

    def create_animation(
        self,
        scenario: Scenario,
        sim_path: Path | None = None,
        bbox: list[float] | None = None,
        zoomlevel: int = 15,
        vmin: float = 0.0,
        vmax: float = 3.0,
    ) -> str:
        """
        Read simulation results from SFINCS and saves an animation of water depths as mp4.

        Produced flood animation is in the units defined in the sfincs config settings.

        Parameters
        ----------
        scenario : Scenario
            Scenario for which to create the floodmap.
        sim_path : Path, optional
            Path to the simulation folder, by default None.
        bbox : list[float], optional
            Bounding box to limit the animation to a specific area (default is None, which means no bounding box).
            Format: [lon_min, lat_min, lon_max, lat_max]
        zoomlevel : int, optional
            Zoom level for the animation (default is 15).
        vmin : float, optional
            Minimum water depth for the color scale (default is 0.0).
        vmax : float, optional
            Maximum water depth for the color scale (default is 3.0).
        """
        logger.info("Creating flood animation.")
        results_path = self._get_result_path(scenario)
        sim_path = sim_path or self._get_simulation_path(scenario)
        demfile = self.database.get_topobathy_path()

        with SfincsAdapter(model_root=sim_path) as model:
            # read water levels
            zs = model._get_zs()

            # read dem
            dem = model._model.data_catalog.get_rasterdataset(demfile, bbox=bbox)

            # convert dem from dem units to floodmap units
            dem_conversion = us.UnitfulLength(
                value=1.0, units=self.settings.dem.units
            ).convert(self.settings.config.floodmap_units)

            # now downscale the water levels to the high-resolution DEM
            # loop through all time steps of zs
            for i in range(zs.shape[0]):
                h = utils.downscale_floodmap(
                    zsmax=zs[i],
                    dep=dem_conversion * dem,
                    hmin=0.01,
                )

                # add the 'time' coordinate
                h["time"] = zs.time[i]

                # create (or append) and xarray DataArray while concatenating along the time dimension
                if i == 0:
                    da_h = h
                else:
                    da_h = xr.concat([da_h, h], dim="time")

        step = 1  # one frame every <step> dtout
        # crs = ccrs.epsg(model._model.crs.to_epsg())
        crs_str = model._model.crs.to_string()

        fig, ax = plt.subplots(1, 1, figsize=(11, 7))

        # first frame
        h0 = da_h.isel(time=0)
        cax_h = h0.plot(
            x="x",
            y="y",
            ax=ax,
            vmin=vmin,
            vmax=vmax,
            cmap="Blues",
            zorder=1,
            cbar_kwargs={
                "shrink": 0.6,
                "label": f"Water depth [{self.settings.config.floodmap_units.value}]",
            },
        )

        # add basemap in the model CRS (contextily will reproject)
        ctx.add_basemap(
            ax,
            crs=crs_str,
            source=ctx.providers.CartoDB.Positron,
            zoom=zoomlevel,
            zorder=0,
        )

        def update_plot(i, da_h, cax_h):
            da_hi = da_h.isel(time=i)
            t = da_hi.time.dt.strftime("%d-%B-%Y %H:%M:%S").item()
            ax.set_title(f"{t}")
            print(f"Adding frame {t}")
            cax_h.set_array(da_hi.to_numpy().ravel())
            return cax_h

        ax.set_aspect("equal", adjustable="box")

        ani = animation.FuncAnimation(
            fig,
            update_plot,
            frames=np.arange(0, da_h.time.size, step),
            interval=100,  # ms between frames
            fargs=(
                da_h,
                cax_h,
            ),
            repeat=False,
        )

        # to save to mp4
        if bbox is not None:
            lon_min = f"{bbox[0]:.2f}".replace(".", "p").replace("-", "m")
            lon_max = f"{bbox[2]:.2f}".replace(".", "p").replace("-", "m")
            fn_out = os.path.join(
                results_path, f"{scenario.name}_lon_{lon_min}_{lon_max}.mp4"
            )
        else:
            fn_out = os.path.join(results_path, f"{scenario.name}.mp4")
        # make sure output directory exists
        os.makedirs(os.path.dirname(fn_out), exist_ok=True)
        ani.save(fn_out, fps=1, dpi=200)

        plt.close(fig)

        logger.info("Flood animation saved.")

        return fn_out

    def write_water_level_map(
        self, scenario: Scenario, sim_path: Optional[Path] = None
    ):
        """Read simulation results from SFINCS and saves a netcdf with the maximum water levels."""
        logger.info("Writing water level map to netcdf")
        results_path = self._get_result_path(scenario)
        sim_path = sim_path or self._get_simulation_path(scenario)

        with SfincsAdapter(model_root=sim_path) as model:
            zsmax = model._get_zsmax()
            if hasattr(zsmax, "ugrid"):
                # First write netcdf with quadtree water levels
                zsmax.to_netcdf(results_path / "max_water_level_map_qt.nc")
                # Rasterize to regular grid with the finest resolution
                zsmax = self._rasterize_quadtree(zsmax)
                # Add CRS to the rasterized xarray
                zsmax = zsmax.rio.write_crs(model._model.config["epsg"])
            # Save as a Cloud Optimized GeoTIFF (COG)
            zsmax.rio.to_raster(
                results_path / "max_water_level_map.tif",
                driver="COG",
                compress="deflate",
                dtype="float32",
                nodata=np.nan,
                OVERVIEW_RESAMPLING="nearest",
                tags={"units": self.settings.config.floodmap_units.value},
            )

    def plot_wl_obs(
        self,
        scenario: Scenario,
    ):
        """Plot water levels at SFINCS observation points as html.

        Only for single event scenarios, or for a specific simulation path containing the written and processed sfincs model.
        """
        if not self.settings.obs_point:
            logger.warning("No observation points provided in config.")
            return

        logger.info("Plotting water levels at observation points")
        sim_path = self._get_simulation_path(scenario)

        # read SFINCS model
        with SfincsAdapter(model_root=sim_path) as model:
            df, gdf = model._get_zs_points()

        gui_units = us.UnitTypesLength(
            self.database.site.gui.units.default_length_units
        )
        conversion_factor = us.UnitfulLength(
            value=1.0, units=us.UnitTypesLength("meters")
        ).convert(gui_units)

        overland_reference_height = self.settings.water_level.get_datum(
            self.settings.config.overland_model.reference
        ).height.convert(gui_units)

        for ii, col in enumerate(df.columns):
            # Plot actual thing
            fig = px.line(
                df[col] * conversion_factor
                + overland_reference_height  # convert to reference datum for plotting
            )

            fig.add_hline(
                y=0,
                line_dash="dash",
                line_color="#000000",
                annotation_text=self.settings.water_level.reference,
                annotation_position="bottom right",
            )

            # plot reference water levels
            for wl_ref in self.settings.water_level.datums:
                if (
                    wl_ref.name == self.settings.config.overland_model.reference
                    or wl_ref.name in self.database.site.gui.plotting.excluded_datums
                ):
                    continue
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
                yaxis_title=f"Water level [{gui_units.value}] above {self.settings.water_level.reference}",
                yaxis_title_font={"size": 10, "color": "black", "family": "Arial"},
                xaxis_title_font={"size": 10, "color": "black", "family": "Arial"},
                showlegend=False,
            )

            event = self.database.events.get(scenario.event)
            if (
                self.settings.tide_gauge is not None
                and self.settings.obs_point[ii].name == self.settings.tide_gauge.name
            ):
                self._add_tide_gauge_plot(fig, event, units=gui_units)

            # write html to results folder
            station_name = gdf.iloc[ii]["Name"]
            results_path = self._get_result_path(scenario)
            fig.write_html(results_path / f"{station_name}_timeseries.html")

    def add_obs_points(self):
        """Add observation points provided in the site toml to SFINCS model."""
        obs_points = self.settings.obs_point
        if not obs_points:
            return

        names = [pt.name for pt in obs_points]
        lat = [pt.lat for pt in obs_points]
        lon = [pt.lon for pt in obs_points]

        logger.info("Adding observation points to the overland flood model")
        df = pd.DataFrame({"name": names})
        gdf = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(lon, lat),
            crs="EPSG:4326",
        )

        # Add locations to SFINCS file
        self._model.setup_observation_points(locations=gdf, merge=False)

    def get_wl_df_from_offshore_his_results(self) -> pd.DataFrame:
        """Create a pd.Dataframe with waterlevels from the offshore model at the bnd locations of the overland model.

        Returns
        -------
        wl_df: pd.DataFrame
            time series of water level.
        """
        logger.info("Reading water levels from offshore model")
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

    ## RISK EVENTS ##
    def calculate_rp_floodmaps(self, scenario: Scenario):
        """Calculate flood risk maps from a set of (currently) SFINCS water level outputs using linear interpolation.

        It would be nice to make it more widely applicable and move the loading of the SFINCS results to self.postprocess_sfincs().

        generates return period water level maps in netcdf format to be used by FIAT
        generates return period water depth maps in geotiff format as product for users

        TODO: make this robust and more efficient for bigger datasets.
        """
        event = self.database.events.get_event_set(scenario.event)
        logger.info("Calculating flood risk maps, this may take some time.")

        # Get the simulation paths and result path
        result_path = self._get_result_path(scenario)
        sim_paths = [
            self._get_simulation_path(scenario, sub_event=sub_event)
            for sub_event in event._events
        ]

        # Get the required return periods for flood maps
        floodmap_rp = self.database.site.fiat.risk.return_periods

        # Get the frequencies for each sub-event
        frequencies = [sub_event.frequency for sub_event in event.sub_events]
        phys_proj = self.database.projections.get(
            scenario.projection
        ).physical_projection

        # adjust storm frequency for hurricane events if provided in the projection
        if not math.isclose(phys_proj.storm_frequency_increase, 0, abs_tol=1e-9):
            storminess_increase = phys_proj.storm_frequency_increase / 100.0
            for ii, event in enumerate(event._events):
                if event.template == Template.Hurricane:
                    frequencies[ii] = frequencies[ii] * (1 + storminess_increase)

        # Read static mask and bed level from the first simulation path
        with SfincsAdapter(model_root=sim_paths[0]) as dummymodel:
            # read mask and bed level
            mask = dummymodel.get_mask()
            zb = dummymodel.get_bedlevel()

        # Read the max water level maps from each simulation path
        zs_maps = []
        for simulation_path in sim_paths:
            # read zsmax data from overland sfincs model
            with SfincsAdapter(model_root=simulation_path) as sim:
                zsmax = sim._get_zsmax().load()
                zs_maps.append(zsmax.values)

        # Calculate return period flood maps
        # All units are in the floodmap units
        rp_flood_maps = self.calc_rp_maps(
            floodmaps=zs_maps,
            frequencies=frequencies,
            zb=zb.values,
            mask=mask.values,
            return_periods=floodmap_rp,
        )

        # convert dem from dem units to floodmap units
        dem_conversion = us.UnitfulLength(
            value=1.0, units=self.settings.dem.units
        ).convert(self.settings.config.floodmap_units)
        dem = self._model.data_catalog.get_rasterdataset(
            self.database.get_topobathy_path()
        )

        # For each return period, save water level and flood depth maps
        for ii, rp in enumerate(floodmap_rp):
            # Prepare data array for the return period flood map
            zs_rp_single = xr.DataArray(
                rp_flood_maps[ii],
                name="zsmax",
                attrs={"units": self.settings.config.floodmap_units.value},
            )
            # If model is quadtree, write the quadtree netcdf with water levels since it is needed for visualizations
            if self._model.grid_type == "quadtree":
                # Use mask grid
                zs_rp_single = xu.UgridDataArray.from_data(
                    zs_rp_single, grid=mask.grid, facet="face"
                )
                # Save to netcdf
                zs_rp_single.to_netcdf(
                    result_path / f"RP_{rp:04d}_max_water_level_map_qt.nc"
                )
                # Rasterize to regular grid with the finest resolution
                zs_rp_single = self._rasterize_quadtree(zs_rp_single)
            # Prepare regular grid water level map
            elif self._model.grid_type == "regular":
                # Create a DataArray with the mask coordinates
                zs_rp_single = xr.DataArray(
                    zs_rp_single,
                    dims=("y", "x"),
                    coords={"y": mask.y, "x": mask.x},
                    name="zsmax",
                )
            else:
                raise ValueError("unsupported sfincs model type")
            # Write COG geotiff with water levels
            zs_rp_single = zs_rp_single.rio.write_crs(self._model.crs)
            fn_rp = result_path / f"RP_{rp:04d}_max_water_level_map.tif"
            zs_rp_single.transpose("y", "x").rio.to_raster(
                fn_rp,
                driver="COG",
                compress="deflate",
                dtype="float32",
                nodata=np.nan,
                OVERVIEW_RESAMPLING="nearest",
                tags={"units": self.settings.config.floodmap_units.value},
            )

            # writing the geotiff to the scenario results folder
            with SfincsAdapter(model_root=sim_paths[0]) as dummymodel:
                floodmap_fn = result_path / f"RP_{rp:04d}_FloodMap.tif"
                utils.downscale_floodmap(
                    zsmax=zs_rp_single,
                    dep=dem_conversion * dem,
                    hmin=0.01,
                    floodmap_fn=floodmap_fn.as_posix(),
                )

    ######################################
    ### PRIVATE - use at your own risk ###
    ######################################
    def _run_single_event(self, scenario: Scenario, event: Event):
        self.preprocess(scenario, event)
        self.process(scenario, event)
        self.postprocess(scenario, event)

        if not self.settings.config.save_simulation:
            self._delete_simulation_folder(scenario, sub_event=event)

    def _delete_simulation_folder(
        self, scenario: Scenario, sub_event: Optional[Event] = None
    ):
        """Delete the simulation folder for a given scenario and optional sub-event."""
        sim_path = self._get_simulation_path(scenario, sub_event=sub_event)
        if sim_path.exists():
            shutil.rmtree(sim_path, ignore_errors=True)
            logger.info(f"Deleted simulation folder: {sim_path}")

        if sim_path.parent.exists() and not any(sim_path.parent.iterdir()):
            # Remove the parent directory `simulations` if it is empty
            shutil.rmtree(sim_path.parent, ignore_errors=True)

    def _run_risk_scenario(self, scenario: Scenario):
        """Run the whole workflow for a risk scenario.

        This means preprocessing and running the SFINCS model for each event in the event set, and then postprocessing the results.
        """
        event_set: EventSet = self.database.events.get_event_set(scenario.event)
        total = len(event_set._events)

        for i, sub_event in enumerate(event_set._events):
            sim_path = self._get_simulation_path(scenario, sub_event=sub_event)

            # Preprocess
            self.preprocess(scenario, event=sub_event)
            logger.info(
                f"Running SFINCS for Eventset Scenario `{scenario.name}`, Event `{sub_event.name}` ({i + 1}/{total})"
            )
            self.execute(sim_path)

        # Postprocess
        self.calculate_rp_floodmaps(scenario)

        # Cleanup
        if not self.settings.config.save_simulation:
            for i, sub_event in enumerate(event_set._events):
                shutil.rmtree(
                    self._get_simulation_path(scenario, sub_event=sub_event),
                    ignore_errors=True,
                )

    def _ensure_no_existing_forcings(self):
        """Check for existing forcings in the model and raise an error if any are found."""
        all_forcings = {
            "waterlevel": self.waterlevels,
            "rainfall": self.rainfall,
            "wind": self.wind,
            "discharge": self.discharge,
        }
        contains_forcings = ", ".join(
            [
                f"{name.capitalize()}"
                for name, forcing in all_forcings.items()
                if forcing is not None
            ]
        )
        if contains_forcings:
            raise ValueError(
                f"{contains_forcings} forcing(s) should not exists in the SFINCS template model. Remove it from the SFINCS model located at: {self.get_model_root()}. For more information on SFINCS and its input files, see the SFINCS documentation at: `https://sfincs.readthedocs.io/en/latest/input.html`"
            )

    ### FORCING ###
    def _add_forcing_wind(
        self,
        wind: IWind,
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
        time_frame = self.get_model_time()
        if isinstance(wind, WindConstant):
            # HydroMT function: set wind forcing from constant magnitude and direction
            self._model.setup_wind_forcing(
                timeseries=None,
                magnitude=wind.speed.convert(us.UnitTypesVelocity.mps),
                direction=wind.direction.value,
            )
        elif isinstance(wind, WindSynthetic):
            df = wind.to_dataframe(time_frame=time_frame)
            df["mag"] *= us.UnitfulVelocity(
                value=1.0, units=self.units.default_velocity_units
            ).convert(us.UnitTypesVelocity.mps)

            tmp_path = Path(tempfile.gettempdir()) / "wind.csv"
            df.to_csv(tmp_path)

            # HydroMT function: set wind forcing from timeseries
            self._model.setup_wind_forcing(
                timeseries=tmp_path, magnitude=None, direction=None
            )
        elif isinstance(wind, WindMeteo):
            ds = MeteoHandler(
                dir=self.database.static_path / "meteo",
                lat=self.database.site.lat,
                lon=self.database.site.lon,
            ).read(time_frame)
            # data already in metric units so no conversion needed

            # HydroMT function: set wind forcing from grid
            self._model.setup_wind_forcing_from_grid(wind=ds)
        elif isinstance(wind, WindTrack):
            # data already in metric units so no conversion needed
            self._add_forcing_spw(wind)
        elif isinstance(wind, WindNetCDF):
            ds = wind.read()
            # time slicing to time_frame not needed, hydromt-sfincs handles it
            conversion = us.UnitfulVelocity(value=1.0, units=wind.units).convert(
                us.UnitTypesVelocity.mps
            )
            ds *= conversion
            self._model.setup_wind_forcing_from_grid(wind=ds)
        elif isinstance(wind, WindCSV):
            df = wind.to_dataframe(time_frame=time_frame)

            conversion = us.UnitfulVelocity(
                value=1.0, units=wind.units["speed"]
            ).convert(us.UnitTypesVelocity.mps)
            df *= conversion

            tmp_path = Path(tempfile.gettempdir()) / "wind.csv"
            df.to_csv(tmp_path)

            # HydroMT function: set wind forcing from timeseries
            self._model.setup_wind_forcing(
                timeseries=tmp_path,
                magnitude=None,
                direction=None,
            )
        else:
            logger.warning(f"Unsupported wind forcing type: {wind.__class__.__name__}")
            return

    def _add_forcing_rain(self, rainfall: IRainfall):
        """Add spatially constant rain forcing to sfincs model. Use timeseries or a constant magnitude.

        Parameters
        ----------
        timeseries : Union[str, os.PathLike], optional
            path to file of timeseries file (.csv) which has two columns: time and precipitation, by default None
        const_intensity : float, optional
            time-invariant precipitation intensity [mm_hr], by default None
        """
        time_frame = self.get_model_time()
        if isinstance(rainfall, RainfallConstant):
            self._model.setup_precip_forcing(
                timeseries=None,
                magnitude=rainfall.intensity.convert(us.UnitTypesIntensity.mm_hr),
            )
        elif isinstance(rainfall, RainfallCSV):
            df = rainfall.to_dataframe(time_frame=time_frame)
            conversion = us.UnitfulIntensity(value=1.0, units=rainfall.units).convert(
                us.UnitTypesIntensity.mm_hr
            )
            df *= conversion

            tmp_path = Path(tempfile.gettempdir()) / "precip.csv"
            df.to_csv(tmp_path)

            self._model.setup_precip_forcing(timeseries=tmp_path)
        elif isinstance(rainfall, RainfallSynthetic):
            df = rainfall.to_dataframe(time_frame=time_frame)

            if rainfall.timeseries.cumulative is not None:  # scs
                conversion = us.UnitfulLength(
                    value=1.0, units=rainfall.timeseries.cumulative.units
                ).convert(us.UnitTypesLength.millimeters)
            else:
                conversion = us.UnitfulIntensity(
                    value=1.0, units=rainfall.timeseries.peak_value.units
                ).convert(us.UnitTypesIntensity.mm_hr)

            df *= conversion
            tmp_path = Path(tempfile.gettempdir()) / "precip.csv"
            df.to_csv(tmp_path)

            self._model.setup_precip_forcing(timeseries=tmp_path)
        elif isinstance(rainfall, RainfallMeteo):
            ds = MeteoHandler(
                dir=self.database.static_path / "meteo",
                lat=self.database.site.lat,
                lon=self.database.site.lon,
            ).read(time_frame)
            # MeteoHandler always return metric so no conversion needed
            self._model.setup_precip_forcing_from_grid(precip=ds, aggregate=False)
        elif isinstance(rainfall, RainfallTrack):
            # data already in metric units so no conversion needed
            self._add_forcing_spw(rainfall)
        elif isinstance(rainfall, RainfallNetCDF):
            ds = rainfall.read()
            # time slicing to time_frame not needed, hydromt-sfincs handles it
            conversion = us.UnitfulIntensity(value=1.0, units=rainfall.units).convert(
                us.UnitTypesIntensity.mm_hr
            )
            ds *= conversion
            self._model.setup_precip_forcing_from_grid(precip=ds, aggregate=False)
        else:
            logger.warning(
                f"Unsupported rainfall forcing type: {rainfall.__class__.__name__}"
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
        if isinstance(forcing, (DischargeConstant, DischargeCSV, DischargeSynthetic)):
            self._set_single_river_forcing(discharge=forcing)
        else:
            logger.warning(
                f"Unsupported discharge forcing type: {forcing.__class__.__name__}"
            )

    def _add_forcing_waterlevels(self, forcing: IWaterlevel):
        time_frame = self.get_model_time()
        if isinstance(forcing, WaterlevelSynthetic):
            df_ts = forcing.to_dataframe(time_frame=time_frame)

            conversion = us.UnitfulLength(
                value=1.0, units=forcing.surge.timeseries.peak_value.units
            ).convert(us.UnitTypesLength.meters)
            datum_correction = self.settings.water_level.get_datum(
                self.database.site.gui.plotting.synthetic_tide.datum
            ).height.convert(us.UnitTypesLength.meters)

            df_ts = df_ts * conversion + datum_correction

            self._set_waterlevel_forcing(df_ts)
        elif isinstance(forcing, WaterlevelGauged):
            if self.settings.tide_gauge is None:
                raise ValueError("No tide gauge defined for this site.")

            df_ts = self.settings.tide_gauge.get_waterlevels_in_time_frame(
                time=time_frame,
            )
            conversion = us.UnitfulLength(
                value=1.0, units=self.settings.tide_gauge.units
            ).convert(us.UnitTypesLength.meters)

            datum_height = self.settings.water_level.get_datum(
                self.settings.tide_gauge.reference
            ).height.convert(us.UnitTypesLength.meters)

            df_ts = conversion * df_ts + datum_height

            self._set_waterlevel_forcing(df_ts)
        elif isinstance(forcing, WaterlevelCSV):
            df_ts = forcing.to_dataframe(time_frame=time_frame)

            if df_ts is None:
                raise ValueError("Failed to get waterlevel data.")
            conversion = us.UnitfulLength(value=1.0, units=forcing.units).convert(
                us.UnitTypesLength.meters
            )
            df_ts *= conversion
            self._set_waterlevel_forcing(df_ts)

        elif isinstance(forcing, WaterlevelModel):
            from flood_adapt.adapter.sfincs_offshore import OffshoreSfincsHandler

            if self.settings.config.offshore_model is None:
                raise ValueError("Offshore model configuration is missing.")
            if self._scenario is None or self._event is None:
                raise ValueError(
                    "Scenario and event must be provided to run the offshore model."
                )

            df_ts = OffshoreSfincsHandler(
                scenario=self._scenario, event=self._event
            ).get_resulting_waterlevels()
            if df_ts is None:
                raise ValueError("Failed to get waterlevel data.")

            # Datum
            datum_correction = self.settings.water_level.get_datum(
                self.settings.config.offshore_model.reference
            ).height.convert(us.UnitTypesLength.meters)
            df_ts += datum_correction

            # Already in meters since it was produced by SFINCS so no conversion needed
            self._set_waterlevel_forcing(df_ts)
            self._turn_off_bnd_press_correction()
        else:
            logger.warning(
                f"Unsupported waterlevel forcing type: {forcing.__class__.__name__}"
            )

    # SPIDERWEB
    def _add_forcing_spw(self, forcing: Union[RainfallTrack, WindTrack]):
        """Add spiderweb forcing."""
        if forcing.source != ForcingSource.TRACK:
            raise ValueError("Forcing source should be TRACK.")

        if forcing.path is None:
            raise ValueError("No path to track file provided.")

        if not forcing.path.exists():
            # Check if the file is in the database
            in_db = self._get_event_input_path(self._event) / forcing.path.name
            if not in_db.exists():
                raise FileNotFoundError(
                    f"Input file for track forcing not found: {forcing.path}"
                )
            forcing.path = in_db

        if forcing.path.suffix == ".cyc":
            forcing.path = self._create_spw_file_from_track(
                track_forcing=forcing,
                hurricane_translation=self._event.hurricane_translation,
                name=self._event.name,
                output_dir=forcing.path.parent,
                include_rainfall=bool(self._event.forcings.get(ForcingType.RAINFALL)),
                recreate=False,
            )

        if forcing.path.suffix != ".spw":
            raise ValueError(
                "Track files should be in one of [spw, ddb_cyc] file format and must have [.spw, .cyc] extension."
            )

        sim_path = self.get_model_root()
        logger.info(f"Adding spiderweb forcing to Sfincs model: {sim_path.name}")

        # prevent SameFileError
        output_spw_path = sim_path / forcing.path.name
        if forcing.path == output_spw_path:
            raise ValueError(
                "Add a different SPW file than the one already in the model."
            )

        if output_spw_path.exists():
            os.remove(output_spw_path)
        shutil.copy2(forcing.path, output_spw_path)

        self._model.set_config("spwfile", output_spw_path.name)

    ### MEASURES ###

    def _convert_z_column_to_meters(
        self, gdf: gpd.GeoDataFrame, z_units: us.UnitTypesLength
    ) -> gpd.GeoDataFrame:
        gdf = gdf.copy()
        gdf["z"] = [
            us.UnitfulLength(value=float(z_val), units=z_units).convert(
                us.UnitTypesLength.meters
            )
            for z_val in gdf["z"]
        ]
        return gdf

    def _add_measure_floodwall(self, floodwall: FloodWall):
        """Add floodwall to sfincs model.

        Parameters
        ----------
        floodwall : FloodWall
            floodwall information
        """
        polygon_file = resolve_filepath(
            object_dir=ObjectDir.measure,
            obj_name=floodwall.name,
            path=floodwall.polygon_file,
        )

        # HydroMT function: get geodataframe from filename
        gdf_floodwall = self._model.data_catalog.get_geodataframe(
            polygon_file, geom=self._model.region, crs=self._model.crs
        )

        # Add floodwall attributes to geodataframe
        gdf_floodwall["name"] = floodwall.name
        if (gdf_floodwall.geometry.type == "MultiLineString").any():
            gdf_floodwall = gdf_floodwall.explode()

        if floodwall.elevation.type == VerticalReference.datum:
            logger.info("Using floodwall height relative to datum.")
            if "z" in gdf_floodwall.columns and gdf_floodwall["z"].notna().all():
                gdf_floodwall = self._convert_z_column_to_meters(
                    gdf_floodwall,
                    self.database.site.gui.units.default_length_units,
                )
                logger.info(
                    f"'z' column with height data found in floodwall shapefile. Each segment will use the respective height above datum in {self.database.site.gui.units.default_length_units}."
                )
            else:
                logger.warning(
                    f"Using uniform height of {floodwall.elevation} above datum."
                )
                gdf_floodwall["z"] = floodwall.elevation.convert(
                    us.UnitTypesLength.meters
                )
        elif floodwall.elevation.type == VerticalReference.floodmap:
            if self.database.site.fiat.config.bfe is None:
                raise ValueError(
                    "Base flood elevation (bfe) map is required to use 'floodmap' as reference for floodwalls."
                )
            bfe_path = self.database.static_path.joinpath(
                self.database.site.fiat.config.bfe.geom
            )
            bfe_field_name = self.database.site.fiat.config.bfe.field_name
            bfe_units = (
                self.database.site.fiat.config.bfe.units
                or self.database.site.gui.units.default_length_units
            )

            gdf_bfe = self._model.data_catalog.get_geodataframe(
                bfe_path, geom=self._model.region, crs=self._model.crs
            )

            if bfe_field_name not in gdf_bfe.columns:
                raise ValueError(
                    f"BFE field '{bfe_field_name}' was not found in {bfe_path}."
                )
            interval = 100.0  # interval in meters to sample the floodwall linestrings for creating points with z values, can be adjusted if needed

            # Convert floodwall elevation to BFE units
            elevation_offset = floodwall.elevation.convert(bfe_units)
            z_conversion = us.UnitfulLength(value=1.0, units=bfe_units).convert(
                us.UnitTypesLength.meters
            )

            gdf_floodwall = create_z_linestrings_from_bfe(
                gdf_lines=gdf_floodwall,
                gdf_bfe=gdf_bfe,
                bfe_field_name=bfe_field_name,
                interval_m=interval,
                elevation_offset=elevation_offset,
                z_conversion=z_conversion,
            )

            if "z" in gdf_floodwall.columns:
                gdf_floodwall = gdf_floodwall.drop(columns=["z"])

            logger.info(
                f"Floodwall height is defined {floodwall.elevation} above Base Flood Elevation (BFE)."
            )
        else:
            raise ValueError(
                f"Unsupported floodwall elevation type: {floodwall.elevation.type}"
            )

        # par1 is the overflow coefficient for weirs
        gdf_floodwall["par1"] = 0.6

        # HydroMT function: create floodwall
        self._model.setup_structures(structures=gdf_floodwall, stype="weir", merge=True)

    def _add_measure_greeninfra(self, green_infrastructure: GreenInfrastructure):
        # HydroMT function: get geodataframe from filename
        if green_infrastructure.selection_type == "polygon":
            polygon_file = resolve_filepath(
                ObjectDir.measure,
                green_infrastructure.name,
                green_infrastructure.polygon_file,
            )
        elif green_infrastructure.selection_type == "aggregation_area":
            # TODO this logic already exists in the Database controller but cannot be used due to cyclic imports
            # Loop through available aggregation area types
            for aggr_dict in self.database.site.fiat.config.aggregation:
                # check which one is used in measure
                if not aggr_dict.name == green_infrastructure.aggregation_area_type:
                    continue
                # load geodataframe
                aggr_areas = gpd.read_file(
                    db_path(TopLevelDir.static) / aggr_dict.file,
                    engine="pyogrio",
                ).to_crs(4326)
                # keep only aggregation area chosen
                polygon_file = aggr_areas.loc[
                    aggr_areas[aggr_dict.field_name]
                    == green_infrastructure.aggregation_area_name,
                    ["geometry"],
                ].reset_index(drop=True)
        else:
            raise ValueError(
                f"The selection type: {green_infrastructure.selection_type} is not valid"
            )

        gdf_green_infra = self._model.data_catalog.get_geodataframe(
            polygon_file,
            geom=self._model.region,
            crs=self._model.crs,
        )

        # Make sure no multipolygons are there
        gdf_green_infra = gdf_green_infra.explode()

        # HydroMT function: create storage volume
        self._model.setup_storage_volume(
            storage_locs=gdf_green_infra,
            volume=green_infrastructure.volume.convert(us.UnitTypesVolume.m3),
            merge=True,
        )

    def _add_measure_pump(self, pump: Pump):
        """Add pump to sfincs model.

        Parameters
        ----------
        pump : Pump
            pump information
        """
        polygon_file = resolve_filepath(ObjectDir.measure, pump.name, pump.polygon_file)
        # HydroMT function: get geodataframe from filename
        gdf_pump = self._model.data_catalog.get_geodataframe(
            polygon_file, geom=self._model.region, crs=self._model.crs
        )

        # HydroMT function: create floodwall
        self._model.setup_drainage_structures(
            structures=gdf_pump,
            stype="pump",
            discharge=pump.discharge.convert(us.UnitTypesDischarge.cms),
            merge=True,
        )

    ### SFINCS SETTERS ###
    def _set_single_river_forcing(self, discharge: IDischarge):
        """Add discharge to overland sfincs model.

        Parameters
        ----------
        discharge : IDischarge
            Discharge object with discharge timeseries data and river information.
        """
        if not isinstance(
            discharge, (DischargeConstant, DischargeSynthetic, DischargeCSV)
        ):
            logger.warning(
                f"Unsupported discharge forcing type: {discharge.__class__.__name__}"
            )
            return

        model_rivers = self._read_river_locations()
        if model_rivers.empty:
            logger.warning(
                "Cannot add discharge forcing: No rivers defined in the sfincs model."
            )
            return
        logger.info(f"Setting discharge forcing for river: {discharge.river.name}")
        time_frame = self.get_model_time()

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
        if isinstance(discharge, DischargeCSV):
            df = discharge.to_dataframe(time_frame)
            conversion = us.UnitfulDischarge(value=1.0, units=discharge.units).convert(
                us.UnitTypesDischarge.cms
            )
        elif isinstance(discharge, DischargeConstant):
            df = discharge.to_dataframe(time_frame)
            conversion = us.UnitfulDischarge(
                value=1.0, units=discharge.discharge.units
            ).convert(us.UnitTypesDischarge.cms)
        elif isinstance(discharge, DischargeSynthetic):
            df = discharge.to_dataframe(time_frame)
            conversion = us.UnitfulDischarge(
                value=1.0, units=discharge.timeseries.peak_value.units
            ).convert(us.UnitTypesDischarge.cms)
        else:
            raise ValueError(
                f"Unsupported discharge forcing type: {discharge.__class__}"
            )

        df *= conversion

        df = df.rename(columns={df.columns[0]: river_inds[0]})

        # HydroMT function: set discharge forcing from time series and river coordinates
        self._model.setup_discharge_forcing(
            locations=river_gdf,
            timeseries=df,
            merge=True,
        )

    def _turn_off_bnd_press_correction(self):
        """Turn off the boundary pressure correction in the sfincs model."""
        logger.info("Turning off boundary pressure correction in the offshore model")
        self._model.set_config("pavbnd", -9999)

    def _set_waterlevel_forcing(self, df_ts: pd.DataFrame):
        """
        Add water level forcing to sfincs model.

        Values in the timeseries are expected to be relative to the main reference datum: `self.settings.water_level.reference`.
        The overland model reference: `self.settings.config.overland_model.reference` is used to convert the water levels to the reference of the overland model.

        Parameters
        ----------
        df_ts : pd.DataFrame
            Time series of water levels with the first column as the time index.


        """
        # Determine bnd points from reference overland model
        gdf_locs = self._read_waterlevel_boundary_locations()

        if len(df_ts.columns) == 1:
            # Go from 1 timeseries to timeseries for all boundary points
            name = df_ts.columns[0]
            for i in range(1, len(gdf_locs)):
                df_ts[i + 1] = df_ts[name]
            df_ts.columns = list(range(1, len(gdf_locs) + 1))

        # Datum
        sfincs_overland_reference_height = self.settings.water_level.get_datum(
            self.settings.config.overland_model.reference
        ).height.convert(us.UnitTypesLength.meters)

        df_ts -= sfincs_overland_reference_height

        # HydroMT function: set waterlevel forcing from time series
        self._model.set_forcing_1d(
            name="bzs", df_ts=df_ts, gdf_locs=gdf_locs, merge=False
        )

    # OFFSHORE
    def _add_pressure_forcing_from_grid(self, ds: xr.DataArray):
        """Add spatially varying barometric pressure to sfincs model.

        Parameters
        ----------
        ds : xr.DataArray
            - Required variables: ['press_msl' (Pa)]
            - Required coordinates: ['time', 'y', 'x']
            - spatial_ref: CRS
        """
        logger.info("Adding pressure forcing to the offshore model")
        self._model.setup_pressure_forcing_from_grid(press=ds)

    def _add_bzs_from_bca(self, event: Event, physical_projection: PhysicalProjection):
        # ONLY offshore models
        """Convert tidal constituents from bca file to waterlevel timeseries that can be read in by hydromt_sfincs."""
        if self.settings.config.offshore_model is None:
            raise ValueError("No offshore model found in sfincs config.")

        logger.info("Adding water level forcing to the offshore model")
        sb = SfincsBoundary()
        sb.read_flow_boundary_points(self.get_model_root() / "sfincs.bnd")
        sb.read_astro_boundary_conditions(self.get_model_root() / "sfincs.bca")

        times = pd.date_range(
            start=event.time.start_time,
            end=event.time.end_time,
            freq="10T",
        )

        # Predict tidal signal and add SLR
        if not sb.flow_boundary_points:
            raise ValueError("No flow boundary points found.")

        if self.settings.config.offshore_model.vertical_offset:
            correction = self.settings.config.offshore_model.vertical_offset.convert(
                us.UnitTypesLength.meters
            )
        else:
            correction = 0.0

        for bnd_ii in range(len(sb.flow_boundary_points)):
            tide_ii = (
                predict(sb.flow_boundary_points[bnd_ii].astro, times)
                + correction
                + physical_projection.sea_level_rise.convert(us.UnitTypesLength.meters)
            )

            if bnd_ii == 0:
                wl_df = pd.DataFrame(data={1: tide_ii}, index=times)
            else:
                wl_df[bnd_ii + 1] = tide_ii

        # Determine bnd points from reference overland model
        gdf_locs = self._read_waterlevel_boundary_locations()

        # HydroMT function: set waterlevel forcing from time series
        self._model.set_forcing_1d(
            name="bzs", df_ts=wl_df, gdf_locs=gdf_locs, merge=False
        )

    ### PRIVATE GETTERS ###
    def _get_result_path(self, scenario: Scenario) -> Path:
        """Return the path to store the results."""
        return self.database.scenarios.output_path / scenario.name / "Flooding"

    def _get_simulation_path(
        self, scenario: Scenario, sub_event: Optional[Event] = None
    ) -> Path:
        """
        Return the path to the simulation results.

        Parameters
        ----------
        scenario : Scenario
            The scenario for which to get the simulation path.
        sub_event : Optional[Event], optional
            The sub-event for which to get the simulation path, by default None.
            Is only used when the event associated with the scenario is an EventSet.
        """
        base_path = (
            self._get_result_path(scenario)
            / "simulations"
            / self.settings.config.overland_model.name
        )
        event = self.database.events.get(scenario.event)

        if isinstance(event, EventSet):
            if sub_event is None:
                raise ValueError("Event must be provided when scenario is an EventSet.")
            return base_path.parent / sub_event.name / base_path.name
        elif isinstance(event, Event):
            return base_path
        else:
            raise ValueError(f"Unsupported mode: {event.mode}")

    def _get_simulation_path_offshore(
        self, scenario: Scenario, sub_event: Optional[Event] = None
    ) -> Path:
        # Get the path to the offshore model (will not be used if offshore model is not created)
        if self.settings.config.offshore_model is None:
            raise ValueError("No offshore model found in sfincs config.")
        base_path = (
            self._get_result_path(scenario)
            / "simulations"
            / self.settings.config.offshore_model.name
        )
        event = self.database.events.get(scenario.event)
        if isinstance(event, EventSet):
            return base_path.parent / sub_event.name / base_path.name
        elif isinstance(event, Event):
            return base_path
        else:
            raise ValueError(f"Unsupported mode: {event.mode}")

    def _get_flood_map_paths(self, scenario: Scenario) -> list[Path]:
        """Return the paths to the flood maps that running this scenario should produce."""
        results_path = self._get_result_path(scenario)
        event = self.database.events.get(scenario.event)

        if isinstance(event, EventSet):
            map_fn = []
            for rp in self.database.site.fiat.risk.return_periods:
                map_fn.append(results_path / f"RP_{rp:04d}_max_water_level_map.tif")
        elif isinstance(event, Event):
            map_fn = [results_path / "max_water_level_map.tif"]
        else:
            raise ValueError(f"Unsupported mode: {event.mode}")

        return map_fn

    def _get_event_input_path(self, event: Event) -> Path:
        """Return the path to the event input directory."""
        return self.database.events.input_path / event.name

    def _get_zsmax(self):
        """Read zsmax file and return absolute maximum water level over entire simulation."""
        self._model.read_results()
        zsmax = self._load_and_copy_results_dataset(
            self._model.results["zsmax"].max(dim="timemax"), "zsmax"
        )

        # Convert from meters to floodmap units
        floodmap_conversion = us.UnitfulLength(
            value=1.0, units=us.UnitTypesLength.meters
        ).convert(self.settings.config.floodmap_units)
        zsmax = zsmax * floodmap_conversion
        zsmax.attrs["units"] = self.settings.config.floodmap_units.value
        return zsmax

    def _get_zs(self):
        """Read zsmax file and return absolute maximum water level over entire simulation."""
        self._model.read_results()
        zs = self._load_and_copy_results_dataset(self._model.results["zs"], "zs")

        # Convert from meters to floodmap units
        floodmap_conversion = us.UnitfulLength(
            value=1.0, units=us.UnitTypesLength.meters
        ).convert(self.settings.config.floodmap_units)
        zs = zs * floodmap_conversion
        zs.attrs["units"] = self.settings.config.floodmap_units.value
        return zs

    def _get_zs_points(self):
        """Read water level (zs) timeseries at observation points.

        Names are allocated from the site.toml.
        See also add_obs_points() above.
        """
        self._model.read_results()
        da = self._model.results["point_zs"]
        df = pd.DataFrame(index=pd.DatetimeIndex(da.time), data=da.to_numpy())

        names = []
        descriptions = []
        # get station names from site.toml
        if self.settings.obs_point is not None:
            obs_points = self.settings.obs_point
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

    def _rasterize_quadtree(self, zsmax: xu.UgridDataArray) -> xr.DataArray:
        """Rasterize the zsmax UgridDataArray to a regular grid."""
        xmin, ymin, xmax, ymax = zsmax.ugrid.bounds["mesh2d"]
        d = self.get_finest_res()
        x = np.arange(xmin + 0.5 * d, xmax, d)
        y = np.arange(ymax - 0.5 * d, ymin, -d)
        # Create a template DataArray with the desired x and y coordinates
        template = xr.DataArray(
            np.zeros((len(y), len(x))),
            coords={"y": y, "x": x},
            dims=("y", "x"),
        )
        zsmax = zsmax.ugrid.rasterize_like(template)
        return zsmax

    def _create_spw_file_from_track(
        self,
        track_forcing: Union[RainfallTrack, WindTrack],
        hurricane_translation: TranslationModel,
        name: str,
        output_dir: Path,
        include_rainfall: bool = False,
        recreate: bool = False,
    ):
        """
        Create a spiderweb file from a given TropicalCyclone track and save it to the event's input directory.

        Providing the output_dir argument allows to save the spiderweb file in a different directory.

        Parameters
        ----------
        output_dir : Path
            The directory where the spiderweb file is saved (or copied to if it already exists and recreate is False)
        recreate : bool, optional
            If True, the spiderweb file is recreated even if it already exists, by default False

        Returns
        -------
        Path
            the path to the created spiderweb file
        """
        if track_forcing.path is None:
            raise ValueError("No path to track file provided.")

        # Check file format
        match track_forcing.path.suffix:
            case ".spw":
                if recreate:
                    raise ValueError(
                        "Recreating spiderweb files from existing spiderweb files is not supported. Provide a track file instead."
                    )

                if track_forcing.path.exists():
                    return track_forcing.path

                elif (output_dir / track_forcing.path.name).exists():
                    return output_dir / track_forcing.path.name

                else:
                    raise FileNotFoundError(f"SPW file not found: {track_forcing.path}")
            case ".cyc":
                pass
            case _:
                raise ValueError(
                    "Track files should be in the DDB_CYC file format and must have .cyc extension, or in the SPW file format and must have .spw extension"
                )

        # Check if the spiderweb file already exists
        spw_file = output_dir / track_forcing.path.with_suffix(".spw").name
        if spw_file.exists():
            if recreate:
                os.remove(spw_file)
            else:
                return spw_file

        # Initialize the tropical cyclone
        tc = TropicalCyclone()
        tc.read_track(filename=track_forcing.path.as_posix(), fmt="ddb_cyc")

        # Alter the track of the tc if necessary
        tc = self._translate_tc_track(
            tc=tc, hurricane_translation=hurricane_translation
        )

        # Rainfall
        start = "Including" if include_rainfall else "Excluding"
        logger.info(f"{start} rainfall in the spiderweb file")
        tc.include_rainfall = include_rainfall

        logger.info(
            f"Creating spiderweb file for hurricane event `{name}`. This may take a while."
        )

        # Create spiderweb file from the track
        tc.to_spiderweb(spw_file)

        return spw_file

    def _translate_tc_track(
        self, tc: TropicalCyclone, hurricane_translation: TranslationModel
    ):
        if math.isclose(
            hurricane_translation.eastwest_translation.value, 0, abs_tol=1e-6
        ) and math.isclose(
            hurricane_translation.northsouth_translation.value, 0, abs_tol=1e-6
        ):
            return tc

        logger.info(f"Translating the track of the tropical cyclone `{tc.name}`")
        # First convert geodataframe to the local coordinate system
        crs = pyproj.CRS.from_string(self.settings.config.csname)
        tc.track = tc.track.to_crs(crs)

        # Translate the track in the local coordinate system
        tc.track["geometry"] = tc.track["geometry"].apply(
            lambda geom: translate(
                geom,
                xoff=hurricane_translation.eastwest_translation.convert(
                    us.UnitTypesLength.meters
                ),
                yoff=hurricane_translation.northsouth_translation.convert(
                    us.UnitTypesLength.meters
                ),
            )
        )

        # Convert the geodataframe to lat/lon
        tc.track = tc.track.to_crs(epsg=4326)

        return tc

    # @gundula do we keep this func, its not used anywhere?
    def _downscale_hmax(self, zsmax, demfile: Path):
        # read DEM and convert units to metric units used by SFINCS
        demfile_units = self.settings.dem.units
        dem_conversion = us.UnitfulLength(value=1.0, units=demfile_units).convert(
            us.UnitTypesLength("meters")
        )
        dem = dem_conversion * self._model.data_catalog.get_rasterdataset(demfile)
        dem = dem.rio.reproject(self._model.crs)

        # determine conversion factor for output floodmap
        floodmap_units = self.settings.config.floodmap_units
        floodmap_conversion = us.UnitfulLength(
            value=1.0, units=us.UnitTypesLength.meters
        ).convert(floodmap_units)

        hmax = utils.downscale_floodmap(
            zsmax=floodmap_conversion * zsmax,
            dep=floodmap_conversion * dem,
            hmin=0.01,
        )
        return hmax

    def _read_river_locations(self) -> gpd.GeoDataFrame:
        path = self.get_model_root() / "sfincs.src"
        lines = []
        if path.exists():
            with open(path) as f:
                lines = f.readlines()
        coords = [(float(line.split()[0]), float(line.split()[1])) for line in lines]
        points = [shapely.Point(coord) for coord in coords]

        return gpd.GeoDataFrame({"geometry": points}, crs=self._model.crs)

    def _read_waterlevel_boundary_locations(self) -> gpd.GeoDataFrame:
        path = self.get_model_root() / "sfincs.bnd"
        lines = []
        if path.exists():
            with open(path) as f:
                lines = f.readlines()

        coords = [(float(line.split()[0]), float(line.split()[1])) for line in lines]
        points = [shapely.Point(coord) for coord in coords]

        return gpd.GeoDataFrame({"geometry": points}, crs=self._model.crs)

    def _setup_sfincs_logger(self, model_root: Path) -> logging.Logger:
        """Initialize the logger for the SFINCS model."""
        # Create a logger for the SFINCS model manually
        sfincs_logger = logging.getLogger("SfincsModel")
        for handler in sfincs_logger.handlers[:]:
            sfincs_logger.removeHandler(handler)

        # Add a file handler
        file_handler = logging.FileHandler(
            filename=model_root.resolve() / "sfincs_model.log",
            mode="w",
        )
        sfincs_logger.setLevel(logging.DEBUG)
        sfincs_logger.addHandler(file_handler)
        self.sfincs_logger = sfincs_logger
        return sfincs_logger

    def _cleanup_simulation_folder(
        self,
        path: Path,
        extensions: list[str] = [".spw"],
    ):
        """Remove all files with the given extensions in the given path."""
        if not path.exists():
            return

        for ext in extensions:
            for file in path.glob(f"*{ext}"):
                file.unlink()

    def _load_scenario_objects(self, scenario: Scenario, event: Event) -> None:
        self._scenario = scenario
        self._projection = self.database.projections.get(scenario.projection)
        self._strategy = self.database.strategies.get(scenario.strategy)
        self._event = event

        _event = self.database.events.get(scenario.event)
        if isinstance(_event, EventSet):
            self._event_set = _event
        else:
            self._event_set = None

    def _add_tide_gauge_plot(
        self, fig, event: Event, units: us.UnitTypesLength
    ) -> None:
        if isinstance(event, SyntheticEvent):
            return
        if self.settings.tide_gauge is None:
            return
        df_gauge = self.settings.tide_gauge.get_waterlevels_in_time_frame(
            time=TimeFrame(
                start_time=event.time.start_time,
                end_time=event.time.end_time,
            ),
            units=us.UnitTypesLength(units),
        )

        if df_gauge is None or df_gauge.empty:
            logger.warning(
                "No water level data available for the tide gauge. Could not add it to the plot."
            )
            return

        gauge_reference_height = self.settings.water_level.get_datum(
            self.settings.tide_gauge.reference
        ).height.convert(units)

        waterlevel = df_gauge.iloc[:, 0] + gauge_reference_height

        # If data is available, add to plot
        fig.add_trace(px.line(waterlevel, color_discrete_sequence=["#ea6404"]).data[0])
        fig["data"][0]["name"] = "model"
        fig["data"][1]["name"] = "measurement"
        fig.update_layout(showlegend=True)

    @staticmethod
    def calc_rp_maps(
        floodmaps: list[np.ndarray],
        frequencies: list[float],
        zb: np.ndarray,
        mask: np.ndarray,
        return_periods: list[float],
    ) -> list[np.ndarray]:
        """
        Calculate return period (RP) flood maps from a set of flood simulation results.

        This function processes multiple flood simulation outputs (water level maps) and their associated frequencies
        to generate hazard maps for specified return periods. It interpolates water levels for each return period
        using exceedance probabilities and handles masked or dry cells appropriately.

        Args:
            floodmaps (list[np.ndarray]): List of water level maps (NumPy arrays), one for each simulation.
            frequencies (list[float]): List of frequencies (probabilities of occurrence) corresponding to each floodmap.
            zb (np.ndarray): Array of bed elevations for each grid cell.
            mask (np.ndarray): Mask indicating valid (1) and invalid (0) grid cells.
            return_periods (list[float]): List of return periods (in years) for which to generate hazard maps.

        Returns
        -------
            list[np.ndarray]: List of NumPy arrays, each representing the hazard map for a given return period.
                            Each array contains water levels (meters) for the corresponding return period.
        """
        floodmaps = [np.asarray(fm) for fm in floodmaps]
        # Check that all floodmaps have the same shape
        first_shape = floodmaps[0].shape
        for i, floodmap in enumerate(floodmaps):
            if floodmap.shape != first_shape:
                raise ValueError(
                    f"Floodmap at index {i} does not match the shape of the first floodmap. "
                    f"Expected shape {first_shape}, got shape {floodmap.shape}."
                )

        # Check that zb and mask have the same shape
        if zb.shape != mask.shape:
            raise ValueError(
                "Bed elevation array (zb) and mask must have the same shape."
            )

        # Check that floodmaps, zb, and mask all have the same shape
        if (
            len(first_shape) != len(zb.shape)
            or first_shape != zb.shape
            or first_shape != mask.shape
        ):
            raise ValueError(
                f"Floodmaps, bed elevation array (zb), and mask must all have the same shape. "
                f"Floodmap shape: {first_shape}, zb shape: {zb.shape}, mask shape: {mask.shape}."
            )

        # If input is 2D, reshape to 1D for processing and then reshape back to 2D
        reshape_needed = False
        if zb.ndim == 2:
            reshape_needed = True
            shape_orig = zb.shape
            n_cells = zb.size
            floodmaps = [fm.reshape(n_cells) for fm in floodmaps]
            zb = zb.reshape(n_cells)
            mask = mask.reshape(n_cells)
        # 1a: make a table of all water levels and associated frequencies
        zs = np.stack(floodmaps, axis=0)
        # Get the indices of columns with all NaN values
        nan_cells = np.where(np.all(np.isnan(zs), axis=0))[0]
        # fill nan values with minimum bed levels in each grid cell, np.interp cannot ignore nan values
        zs = np.where(np.isnan(zs), np.tile(zb, (zs.shape[0], 1)), zs)
        # Get table of frequencies
        freq = np.tile(frequencies, (zs.shape[1], 1)).transpose()

        # 1b: sort water levels in descending order and include the frequencies in the sorting process
        # (i.e. each h-value should be linked to the same p-values as in step 1a)
        sort_index = zs.argsort(axis=0)
        sorted_prob = np.flipud(np.take_along_axis(freq, sort_index, axis=0))
        sorted_zs = np.flipud(np.take_along_axis(zs, sort_index, axis=0))

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

        valid_cells = np.where(mask == 1)[
            0
        ]  # only loop over cells where model is not masked
        h = np.tile(
            zb, (len(return_periods), 1)
        )  # if not flooded (i.e. not in valid_cells) revert to bed_level, read from SFINCS results so it is the minimum bed level in a grid cell

        for jj in valid_cells:  # looping over all non-masked cells.
            # linear interpolation for all return periods to evaluate
            h[:, jj] = np.interp(
                np.log10(return_periods),
                np.log10(rp_zs[::-1, jj]),
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

        rp_maps = []
        for ii, rp in enumerate(return_periods):
            rp_maps.append(h[ii, :])

        if reshape_needed:
            # Reshape back to 2D if needed
            rp_maps = [rp_map.reshape(shape_orig) for rp_map in rp_maps]

        return rp_maps

    def _load_and_copy_results_dataset(
        self, dataset: xr.Dataset, result_name: str
    ) -> xr.Dataset:
        """Load a dataset from the model results and return a deep copy of it."""
        # load to read in any lazy datasets
        # copy to avoid keeping the file handle open for lazy loading
        ds = dataset.load().copy(deep=True)
        try:
            # delete the dataset from the model results to mark it for garbage collection
            del self._model.results[result_name]
        except Exception:
            pass
        # force collect
        gc.collect()
        return ds
