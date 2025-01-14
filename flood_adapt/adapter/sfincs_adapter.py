import logging
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Union

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

from flood_adapt.adapter.interface.hazard_adapter import IHazardAdapter
from flood_adapt.misc.config import Settings
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.object_model.hazard.event.event_set import EventSet
from flood_adapt.object_model.hazard.event.historical import HistoricalEvent
from flood_adapt.object_model.hazard.forcing.discharge import (
    DischargeConstant,
    DischargeCSV,
    DischargeSynthetic,
)
from flood_adapt.object_model.hazard.forcing.meteo_handler import MeteoHandler
from flood_adapt.object_model.hazard.forcing.rainfall import (
    RainfallConstant,
    RainfallCSV,
    RainfallMeteo,
    RainfallSynthetic,
    RainfallTrack,
)
from flood_adapt.object_model.hazard.forcing.tide_gauge import TideGauge
from flood_adapt.object_model.hazard.forcing.timeseries import (
    CSVTimeseries,
)
from flood_adapt.object_model.hazard.forcing.waterlevels import (
    WaterlevelCSV,
    WaterlevelGauged,
    WaterlevelModel,
    WaterlevelSynthetic,
)
from flood_adapt.object_model.hazard.forcing.wind import (
    WindConstant,
    WindMeteo,
    WindSynthetic,
    WindTrack,
)
from flood_adapt.object_model.hazard.interface.events import IEvent, Template
from flood_adapt.object_model.hazard.interface.forcing import (
    IDischarge,
    IForcing,
    IRainfall,
    IWaterlevel,
    IWind,
)
from flood_adapt.object_model.hazard.interface.models import TimeModel
from flood_adapt.object_model.hazard.measure.floodwall import FloodWall
from flood_adapt.object_model.hazard.measure.green_infrastructure import (
    GreenInfrastructure,
)
from flood_adapt.object_model.hazard.measure.pump import Pump
from flood_adapt.object_model.interface.config.site import Site
from flood_adapt.object_model.interface.measures import IMeasure
from flood_adapt.object_model.interface.path_builder import (
    ObjectDir,
    TopLevelDir,
    db_path,
)
from flood_adapt.object_model.interface.projections import (
    IProjection,
    PhysicalProjectionModel,
)
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.io import unit_system as us
from flood_adapt.object_model.utils import cd, resolve_filepath


class SfincsAdapter(IHazardAdapter):
    logger = FloodAdaptLogging.getLogger(__name__)
    _site: Site
    _model: SfincsModel

    ###############
    ### PUBLIC ####
    ###############

    ### HAZARD ADAPTER METHODS ###
    def __init__(self, model_root: Path):
        """Load overland sfincs model based on a root directory.

        Args:
            model_root (Path): Root directory of overland sfincs model.
        """
        self.site = self.database.site

        self.sfincs_logger = FloodAdaptLogging.getLogger(
            "hydromt_sfincs", level=logging.DEBUG
        )
        self._model = SfincsModel(
            root=str(model_root.resolve()), mode="r", logger=self.sfincs_logger
        )
        self._model.read()

    def read(self, path: Path):
        """Read the sfincs model from the current model root."""
        if Path(self._model.root).resolve() != Path(path).resolve():
            self._model.set_root(root=str(path), mode="r")
        self._model.read()

    def write(self, path_out: Union[str, os.PathLike], overwrite: bool = True):
        """Write the sfincs model configuration to a directory."""
        root = self.get_model_root()
        if not isinstance(path_out, Path):
            path_out = Path(path_out).resolve()

        if not path_out.exists():
            path_out.mkdir(parents=True)

        write_mode = "w+" if overwrite else "w"
        with cd(path_out):
            shutil.copytree(root, path_out, dirs_exist_ok=True)

            self._model.set_root(root=str(path_out), mode=write_mode)
            self._model.write()
            self._model.set_root(root=str(root), mode=write_mode)

    def close_files(self):
        """Close all open files and clean up file handles."""
        for logger in [self.logger, self.sfincs_logger]:
            if hasattr(logger, "handlers"):
                for handler in logger.handlers:
                    if isinstance(handler, logging.FileHandler):
                        handler.close()
                        self.logger.removeHandler(handler)

    def __enter__(self) -> "SfincsAdapter":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        self.close_files()
        return False

    def ensure_no_existing_forcings(self):
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

    def has_run(self, scenario: IScenario) -> bool:
        """Check if the model has been run."""
        return self.sfincs_completed(scenario) and self.run_completed(scenario)

    def execute(self, path: Path, strict: bool = True) -> bool:
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
        sfincs_log = path / "sfincs.log"
        with cd(path):
            with FloodAdaptLogging.to_file(file_path=sfincs_log):
                self.logger.info(f"Running SFINCS in {path}...")
                process = subprocess.run(
                    str(Settings().sfincs_path),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                self.logger.debug(process.stdout)

        if process.returncode != 0:
            if Settings().delete_crashed_runs:
                # Remove all files in the simulation folder except for the log files
                for subdir, dirs, files in os.walk(path, topdown=False):
                    for file in files:
                        if not file.endswith(".log"):
                            os.remove(os.path.join(subdir, file))

                    if not os.listdir(subdir):
                        os.rmdir(subdir)

            if strict:
                raise RuntimeError(f"SFINCS model failed to run in {path}.")
            else:
                self.logger.error(f"SFINCS model failed to run in {path}.")

        return process.returncode == 0

    def run(self, scenario: IScenario):
        """Run the whole workflow (Preprocess, process and postprocess) for a given scenario."""
        self.ensure_no_existing_forcings()
        self.preprocess(scenario)
        self.process(scenario)
        self.postprocess(scenario)

    def preprocess(self, scenario: IScenario):
        sim_paths = self._get_simulation_paths(scenario)

        if isinstance(scenario.event, EventSet):
            self._preprocess_risk(scenario, sim_paths)
        elif isinstance(scenario.event, IEvent):
            self._preprocess_single_event(scenario, output_path=sim_paths[0])

    def process(self, scenario: IScenario):
        sim_paths = self._get_simulation_paths(scenario)
        if isinstance(scenario.event, IEvent):
            self.execute(sim_paths[0])

        elif isinstance(scenario.event, EventSet):
            for sim_path in sim_paths:
                self.execute(sim_path)

                # postprocess subevents to be able to calculate return periods
                self.write_floodmap_geotiff(scenario, sim_path=sim_path)
                self.plot_wl_obs(scenario, sim_path=sim_path)
                self.write_water_level_map(scenario, sim_path=sim_path)

    def postprocess(self, scenario: IScenario):
        if not self.sfincs_completed(scenario):
            raise RuntimeError("SFINCS was not run successfully!")

        if isinstance(scenario.event, IEvent):
            self.write_floodmap_geotiff(scenario)
            self.plot_wl_obs(scenario)
            self.write_water_level_map(scenario)

        elif isinstance(scenario.event, EventSet):
            self.calculate_rp_floodmaps(scenario)

    def set_timing(self, time: TimeModel):
        """Set model reference times."""
        self._model.set_config("tref", time.start_time)
        self._model.set_config("tstart", time.start_time)
        self._model.set_config("tstop", time.end_time)

    def add_forcing(self, forcing: IForcing):
        """Get forcing data and add it to the sfincs model."""
        if forcing is None:
            return

        self.logger.info(
            f"Adding {forcing.type.capitalize()} (source: {forcing.source.lower()}) to the SFINCS model..."
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
            self.logger.warning(
                f"Skipping unsupported forcing type {forcing.__class__.__name__}"
            )

    def add_measure(self, measure: IMeasure):
        """Get measure data and add it to the sfincs model."""
        self.logger.info(
            f"Adding {measure.__class__.__name__.capitalize()} to the SFINCS model..."
        )

        if isinstance(measure, FloodWall):
            self._add_measure_floodwall(measure)
        elif isinstance(measure, GreenInfrastructure):
            self._add_measure_greeninfra(measure)
        elif isinstance(measure, Pump):
            self._add_measure_pump(measure)
        else:
            self.logger.warning(
                f"Skipping unsupported measure type {measure.__class__.__name__}"
            )

    def add_projection(self, projection: IProjection):
        """Get forcing data currently in the sfincs model and add the projection it."""
        self.logger.info("Adding Projection to the SFINCS model...")
        phys_projection = projection.get_physical_projection()

        if phys_projection.attrs.sea_level_rise:
            self.logger.info(
                f"Adding projected sea level rise ({phys_projection.attrs.sea_level_rise}) to SFINCS model."
            )
            if self.waterlevels is not None:
                self.waterlevels += phys_projection.attrs.sea_level_rise.convert(
                    us.UnitTypesLength.meters
                )
            else:
                self.logger.warning(
                    "Failed to add sea level rise, no water level forcing found in the model."
                )

        if phys_projection.attrs.rainfall_multiplier:
            self.logger.info(
                f"Adding projected rainfall multiplier ({phys_projection.attrs.rainfall_multiplier}) to SFINCS model."
            )
            if self.rainfall is not None:
                self.rainfall *= phys_projection.attrs.rainfall_multiplier
            else:
                self.logger.warning(
                    "Failed to add projected rainfall multiplier, no rainfall forcing found in the model."
                )

    ### GETTERS ###
    def get_model_root(self) -> Path:
        return Path(self._model.root)

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
        elif len(in_model) == 2:
            return xr.Dataset(
                {
                    "wind10_u": self._model.forcing["wind10_u"],
                    "wind10_v": self._model.forcing["wind10_v"],
                }
            )
        else:
            raise ValueError("Multiple wind forcings found in the model.")

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
    def run_completed(self, scenario: IScenario) -> bool:
        """Check if the entire model run has been completed successfully by checking if all flood maps exist that are created in postprocess().

        Returns
        -------
        bool : True if all flood maps exist, False otherwise.

        """
        any_floodmap = len(self._get_flood_map_paths(scenario)) > 0
        all_exist = all(
            floodmap.exists() for floodmap in self._get_flood_map_paths(scenario)
        )
        return any_floodmap and all_exist

    def sfincs_completed(self, scenario: IScenario) -> bool:
        """Check if the sfincs executable has been run successfully by checking if the output files exist in the simulation folder.

        Returns
        -------
        bool: True if the sfincs executable has been run successfully, False otherwise.

        """
        sim_paths = self._get_simulation_paths(scenario)
        SFINCS_OUTPUT_FILES = ["sfincs_his.nc", "sfincs_map.nc"]

        if isinstance(scenario.event, EventSet):
            for sim_path in sim_paths:
                to_check = [Path(sim_path) / file for file in SFINCS_OUTPUT_FILES]
                if not all(output.exists() for output in to_check):
                    return False
            return True
        elif isinstance(scenario.event, IEvent):
            to_check = [Path(sim_paths[0]) / file for file in SFINCS_OUTPUT_FILES]
            # Add logfile check as well from old hazard.py?
            return all(output.exists() for output in to_check)
        else:
            raise ValueError(f"Unsupported event type: {type(scenario.event)}.")

    def write_floodmap_geotiff(
        self, scenario: IScenario, sim_path: Optional[Path] = None
    ):
        results_path = self._get_result_path(scenario)
        sim_path = sim_path or self._get_simulation_paths(scenario)[0]
        demfile = (
            self.database.static_path / "dem" / self.site.attrs.sfincs.dem.filename
        )

        # read SFINCS model
        with SfincsAdapter(model_root=sim_path) as model:
            zsmax = model._get_zsmax()
            dem = model._model.data_catalog.get_rasterdataset(demfile)

            # writing the geotiff to the scenario results folder
            model.write_geotiff(
                zsmax=zsmax,
                dem=dem,
                dem_units=us.UnitTypesLength(us.UnitTypesLength.meters),
                floodmap_fn=results_path / f"FloodMap_{scenario.attrs.name}.tif",
                floodmap_units=us.UnitTypesLength(us.UnitTypesLength.meters),
            )

    def write_water_level_map(
        self, scenario: IScenario, sim_path: Optional[Path] = None
    ):
        """Read simulation results from SFINCS and saves a netcdf with the maximum water levels."""
        results_path = self._get_result_path(scenario)
        sim_path = sim_path or self._get_simulation_paths(scenario)[0]

        with SfincsAdapter(model_root=sim_path) as model:
            zsmax = model._get_zsmax()
            zsmax.to_netcdf(results_path / "max_water_level_map.nc")

    @staticmethod
    def write_geotiff(
        zsmax,
        dem,
        dem_units: us.UnitTypesLength,
        floodmap_fn: Path,
        floodmap_units: us.UnitTypesLength,
    ):
        # read DEM and convert units to metric units used by SFINCS
        dem_conversion = us.UnitfulLength(value=1.0, units=dem_units).convert(
            us.UnitTypesLength(us.UnitTypesLength.meters)
        )
        # determine conversion factor for output floodmap
        floodmap_conversion = us.UnitfulLength(
            value=1.0, units=us.UnitTypesLength(floodmap_units)
        ).convert(us.UnitTypesLength.meters)

        utils.downscale_floodmap(
            zsmax=floodmap_conversion * zsmax,
            dep=dem_conversion * dem,
            hmin=0.01,
            floodmap_fn=str(floodmap_fn),
        )

    def plot_wl_obs(
        self,
        scenario: IScenario,
        sim_path: Optional[Path] = None,
        event: Optional[IEvent] = None,
    ):
        """Plot water levels at SFINCS observation points as html.

        Only for single event scenarios, or for a specific simulation path containing the written and processed sfincs model.
        """
        sim_path = sim_path or self._get_simulation_paths(scenario)[0]
        event = event or scenario.event

        # read SFINCS model
        with SfincsAdapter(model_root=sim_path) as model:
            df, gdf = model._get_zs_points()

        gui_units = us.UnitTypesLength(self.site.attrs.gui.units.default_length_units)
        conversion_factor = us.UnitfulLength(
            value=1.0, units=us.UnitTypesLength("meters")
        ).convert(gui_units)

        for ii, col in enumerate(df.columns):
            # Plot actual thing
            fig = px.line(
                df[col] * conversion_factor
                + self.site.attrs.sfincs.water_level.localdatum.height.convert(
                    gui_units
                )  # convert to reference datum for plotting
            )

            # plot reference water levels
            fig.add_hline(
                y=self.site.attrs.sfincs.water_level.msl.height.convert(gui_units),
                line_dash="dash",
                line_color="#000000",
                annotation_text=self.site.attrs.sfincs.water_level.msl.name,
                annotation_position="bottom right",
            )
            if self.site.attrs.sfincs.water_level.other:
                for wl_ref in self.site.attrs.sfincs.water_level.other:
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
                if self.site.attrs.sfincs.tide_gauge is None:
                    continue
                df_gauge = TideGauge(
                    attrs=self.site.attrs.sfincs.tide_gauge
                ).get_waterlevels_in_time_frame(
                    time=TimeModel(
                        start_time=event.attrs.time.start_time,
                        end_time=event.attrs.time.end_time,
                    ),
                    units=us.UnitTypesLength(gui_units),
                )

                if df_gauge is not None:
                    waterlevel = df_gauge.iloc[
                        :, 0
                    ] + self.site.attrs.sfincs.water_level.msl.height.convert(gui_units)

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
            results_path = self._get_result_path(scenario)
            fig.write_html(results_path / f"{station_name}_timeseries.html")

    def add_obs_points(self):
        """Add observation points provided in the site toml to SFINCS model."""
        if self.site.attrs.sfincs.obs_point is not None:
            self.logger.info("Adding observation points to the overland flood model...")

            obs_points = self.site.attrs.sfincs.obs_point
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

    def get_wl_df_from_offshore_his_results(self) -> pd.DataFrame:
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

    ## RISK EVENTS ##
    def calculate_rp_floodmaps(self, scenario: IScenario):
        """Calculate flood risk maps from a set of (currently) SFINCS water level outputs using linear interpolation.

        It would be nice to make it more widely applicable and move the loading of the SFINCS results to self.postprocess_sfincs().

        generates return period water level maps in netcdf format to be used by FIAT
        generates return period water depth maps in geotiff format as product for users

        TODO: make this robust and more efficient for bigger datasets.
        """
        if not isinstance(scenario.event, EventSet):
            raise ValueError("This function is only available for risk scenarios.")

        result_path = self._get_result_path(scenario)
        sim_paths = self._get_simulation_paths(scenario)

        phys_proj = scenario.projection.get_physical_projection()

        floodmap_rp = self.site.attrs.fiat.risk.return_periods
        frequencies = scenario.event.attrs.frequency

        # adjust storm frequency for hurricane events
        if not math.isclose(phys_proj.attrs.storm_frequency_increase, 0):
            storminess_increase = phys_proj.attrs.storm_frequency_increase / 100.0
            for ii, event in enumerate(scenario.event.events):
                if event.attrs.template == Template.Hurricane:
                    frequencies[ii] = frequencies[ii] * (1 + storminess_increase)

        with SfincsAdapter(model_root=sim_paths[0]) as dummymodel:
            # read mask and bed level
            mask = dummymodel.get_mask().stack(z=("x", "y"))
            zb = dummymodel.get_bedlevel().stack(z=("x", "y")).to_numpy()

        zs_maps = []
        for simulation_path in sim_paths:
            # read zsmax data from overland sfincs model
            with SfincsAdapter(model_root=simulation_path) as sim:
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
                self.database.static_path / "dem" / self.site.attrs.sfincs.dem.filename
            )

            # writing the geotiff to the scenario results folder
            with SfincsAdapter(model_root=sim_paths[0]) as dummymodel:
                dem = dummymodel._model.data_catalog.get_rasterdataset(demfile)
                zsmax = zs_rp_single.to_array().squeeze().transpose()

                dummymodel.write_geotiff(
                    zsmax=zsmax,
                    dem=dem,
                    dem_units=us.UnitTypesLength.meters,
                    floodmap_fn=result_path / f"RP_{rp:04d}_maps.tif",
                    floodmap_units=us.UnitTypesLength.meters,
                )

    ######################################
    ### PRIVATE - use at your own risk ###
    ######################################
    def _preprocess_single_event(
        self, scenario: IScenario, output_path: Path, event: Optional[IEvent] = None
    ):
        # Use the event from the scenario if not provided by event sets
        if event is None:
            event = scenario.event

        # Write template model to output path and set it as the model root so focings can write to it
        self.set_timing(event.attrs.time)
        self.write(output_path)

        # I dont like this due to it being state based and might break if people use functions in the wrong order
        # Currently only used to pass projection + event stuff to WaterlevelModel
        self._current_scenario = scenario
        try:
            # Event
            for forcing in event.get_forcings():
                self.add_forcing(forcing)

            if self.rainfall is not None:
                self.rainfall *= event.attrs.rainfall_multiplier
            else:
                self.logger.warning(
                    "Failed to add event rainfall multiplier, no rainfall forcing found in the model."
                )

            # Measures
            for measure in scenario.strategy.get_hazard_strategy().measures:
                self.add_measure(measure)

            # Projection
            self.add_projection(scenario.projection)

            # Output
            self.add_obs_points()

            # Save any changes made to disk as well
            self.write(path_out=output_path)

        finally:
            self._current_scenario = None

    def _preprocess_risk(self, scenario: IScenario, sim_paths: List[Path]):
        if not isinstance(scenario.event, EventSet):
            raise ValueError("This function is only available for risk scenarios.")
        if not len(sim_paths) == len(scenario.event.events):
            raise ValueError(
                "Number of simulation paths should match the number of events."
            )

        for sub_event, sim_path in zip(scenario.event.events, sim_paths):
            self._preprocess_single_event(
                scenario, output_path=sim_path, event=sub_event
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
        t0, t1 = self._model.get_model_time()

        if isinstance(wind, WindConstant):
            # HydroMT function: set wind forcing from constant magnitude and direction
            self._model.setup_wind_forcing(
                timeseries=None,
                magnitude=wind.speed.convert(us.UnitTypesVelocity.mps),
                direction=wind.direction.value,
            )
        elif isinstance(wind, WindSynthetic):
            df = wind.to_dataframe(time_frame=TimeModel(start_time=t0, end_time=t1))
            df["mag"] *= us.UnitfulVelocity(
                value=1.0, units=Settings().unit_system.velocity
            ).convert(us.UnitTypesVelocity.mps)

            tmp_path = Path(tempfile.gettempdir()) / "wind.csv"
            df.to_csv(tmp_path)

            # HydroMT function: set wind forcing from timeseries
            self._model.setup_wind_forcing(
                timeseries=tmp_path, magnitude=None, direction=None
            )
        elif isinstance(wind, WindMeteo):
            ds = MeteoHandler().read(TimeModel(start_time=t0, end_time=t1))
            # data already in metric units so no conversion needed

            # HydroMT function: set wind forcing from grid
            self._model.setup_wind_forcing_from_grid(wind=ds)
        elif isinstance(wind, WindTrack):
            if wind.path is None:
                raise ValueError("No path to rainfall track file provided.")
            # data already in metric units so no conversion needed
            self._add_forcing_spw(wind.path)
        else:
            self.logger.warning(
                f"Unsupported wind forcing type: {wind.__class__.__name__}"
            )
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
        t0, t1 = self._model.get_model_time()
        time_frame = TimeModel(start_time=t0, end_time=t1)
        if isinstance(rainfall, RainfallConstant):
            self._model.setup_precip_forcing(
                timeseries=None,
                magnitude=rainfall.intensity.convert(us.UnitTypesIntensity.mm_hr),
            )
        elif isinstance(rainfall, RainfallCSV):
            df = rainfall.to_dataframe(time_frame=time_frame)
            conversion = us.UnitfulIntensity(value=1.0, units=rainfall.unit).convert(
                us.UnitTypesIntensity.mm_hr
            )
            df *= self._current_scenario.event.attrs.rainfall_multiplier * conversion
        elif isinstance(rainfall, RainfallSynthetic):
            df = rainfall.to_dataframe(time_frame=time_frame)
            conversion = us.UnitfulIntensity(
                value=1.0, units=rainfall.timeseries.peak_value.units
            ).convert(us.UnitTypesIntensity.mm_hr)
            df *= self._current_scenario.event.attrs.rainfall_multiplier * conversion

            tmp_path = Path(tempfile.gettempdir()) / "precip.csv"
            df.to_csv(tmp_path)

            self._model.setup_precip_forcing(timeseries=tmp_path)
        elif isinstance(rainfall, RainfallMeteo):
            ds = MeteoHandler().read(time_frame)
            # data already in metric units so no conversion needed
            self._model.setup_precip_forcing_from_grid(precip=ds, aggregate=False)
        elif isinstance(rainfall, RainfallTrack):
            if rainfall.path is None:
                raise ValueError("No path to rainfall track file provided.")
            # data already in metric units so no conversion needed
            self._add_forcing_spw(rainfall.path)
        else:
            self.logger.warning(
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
            self.logger.warning(
                f"Unsupported discharge forcing type: {forcing.__class__.__name__}"
            )

    def _add_forcing_waterlevels(self, forcing: IWaterlevel):
        t0, t1 = self._model.get_model_time()
        time_frame = TimeModel(start_time=t0, end_time=t1)
        if isinstance(forcing, WaterlevelSynthetic):
            df_ts = forcing.to_dataframe(time_frame=time_frame)
            conversion = us.UnitfulLength(
                value=1.0, units=forcing.surge.timeseries.peak_value.units
            ).convert(us.UnitTypesLength.meters)
            df_ts *= conversion
            self._set_waterlevel_forcing(df_ts)
        elif isinstance(forcing, WaterlevelGauged):
            if self.site.attrs.sfincs.tide_gauge is None:
                raise ValueError("No tide gauge defined for this site.")
            df_ts = TideGauge(
                self.site.attrs.sfincs.tide_gauge
            ).get_waterlevels_in_time_frame(time=time_frame)
            conversion = us.UnitfulLength(
                value=1.0, units=self.site.attrs.sfincs.tide_gauge.units
            ).convert(us.UnitTypesLength.meters)
            df_ts *= conversion
            self._set_waterlevel_forcing(df_ts)
        elif isinstance(forcing, WaterlevelCSV):
            df_ts = CSVTimeseries.load_file(path=forcing.path).to_dataframe(
                time_frame=time_frame
            )
            if df_ts is None:
                raise ValueError("Failed to get waterlevel data.")

            conversion = us.UnitfulLength(value=1.0, units=forcing.units).convert(
                us.UnitTypesLength.meters
            )
            df_ts *= conversion
            self._set_waterlevel_forcing(df_ts)

        elif isinstance(forcing, WaterlevelModel):
            from flood_adapt.adapter.sfincs_offshore import OffshoreSfincsHandler

            if self._current_scenario is None:
                raise ValueError("Scenario must be provided to run the offshore model.")

            df_ts = OffshoreSfincsHandler().get_resulting_waterlevels(
                scenario=self._current_scenario
            )
            if df_ts is None:
                raise ValueError("Failed to get waterlevel data.")

            # Already in meters since it was produced by SFINCS so no conversion needed
            self._set_waterlevel_forcing(df_ts)
            self._turn_off_bnd_press_correction()
        else:
            self.logger.warning(
                f"Unsupported waterlevel forcing type: {forcing.__class__.__name__}"
            )

    ### MEASURES ###
    def _add_measure_floodwall(self, floodwall: FloodWall):
        """Add floodwall to sfincs model.

        Parameters
        ----------
        floodwall : FloodWallModel
            floodwall information
        """
        self.logger.info("Adding floodwall to the overland flood model...")

        polygon_file = resolve_filepath(
            object_dir=ObjectDir.measure,
            obj_name=floodwall.attrs.name,
            path=floodwall.attrs.polygon_file,
        )

        # HydroMT function: get geodataframe from filename
        gdf_floodwall = self._model.data_catalog.get_geodataframe(
            polygon_file, geom=self._model.region, crs=self._model.crs
        )

        # Add floodwall attributes to geodataframe
        gdf_floodwall["name"] = floodwall.attrs.name
        gdf_floodwall["name"] = floodwall.attrs.name
        if (gdf_floodwall.geometry.type == "MultiLineString").any():
            gdf_floodwall = gdf_floodwall.explode()

        try:
            heights = [
                float(
                    us.UnitfulLength(
                        value=float(height),
                        units=self.site.attrs.gui.default_length_units,
                    ).convert(us.UnitTypesLength("meters"))
                )
                for height in gdf_floodwall["z"]
            ]
            gdf_floodwall["z"] = heights
            self.logger.info("Using floodwall height from shape file.")
        except Exception:
            self.logger.warning(
                f"""Could not use height data from file due to missing ""z""-column or missing values therein.\n
                Using uniform height of {floodwall.attrs.elevation.convert(us.UnitTypesLength("meters"))} meters instead."""
            )
            gdf_floodwall["z"] = floodwall.attrs.elevation.convert(
                us.UnitTypesLength("meters")
            )

        # par1 is the overflow coefficient for weirs
        gdf_floodwall["par1"] = 0.6

        # HydroMT function: create floodwall
        self._model.setup_structures(structures=gdf_floodwall, stype="weir", merge=True)

    def _add_measure_greeninfra(self, green_infrastructure: GreenInfrastructure):
        self.logger.info("Adding green infrastructure to the overland flood model...")

        # HydroMT function: get geodataframe from filename
        if green_infrastructure.attrs.selection_type == "polygon":
            polygon_file = resolve_filepath(
                ObjectDir.measure,
                green_infrastructure.attrs.name,
                green_infrastructure.attrs.polygon_file,
            )
        elif green_infrastructure.attrs.selection_type == "aggregation_area":
            # TODO this logic already exists in the Database controller but cannot be used due to cyclic imports
            # Loop through available aggregation area types
            for aggr_dict in self.site.attrs.fiat.aggregation:
                # check which one is used in measure
                if (
                    not aggr_dict.name
                    == green_infrastructure.attrs.aggregation_area_type
                ):
                    continue
                # load geodataframe
                aggr_areas = gpd.read_file(
                    db_path(TopLevelDir.static) / aggr_dict.file,
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
        volume = green_infrastructure.attrs.volume.convert(us.UnitTypesVolume("m3"))
        volume = green_infrastructure.attrs.volume.convert(us.UnitTypesVolume("m3"))

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
        self.logger.info("Adding pump to the overland flood model...")

        polygon_file = resolve_filepath(
            ObjectDir.measure, pump.attrs.name, pump.attrs.polygon_file
        )
        # HydroMT function: get geodataframe from filename
        gdf_pump = self._model.data_catalog.get_geodataframe(
            polygon_file, geom=self._model.region, crs=self._model.crs
        )

        # HydroMT function: create floodwall
        self._model.setup_drainage_structures(
            structures=gdf_pump,
            stype="pump",
            discharge=pump.attrs.discharge.convert(us.UnitTypesDischarge.cms),
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
            self.logger.warning(
                f"Unsupported discharge forcing type: {discharge.__class__.__name__}"
            )
            return

        self.logger.info(f"Setting discharge forcing for river: {discharge.river.name}")
        t0, t1 = self._model.get_model_time()
        time_frame = TimeModel(start_time=t0, end_time=t1)
        model_rivers = self._read_river_locations()

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
            conversion = us.UnitfulDischarge(value=1.0, units=discharge.unit).convert(
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
        self._model.set_config("pavbnd", -9999)

    def _set_waterlevel_forcing(self, df_ts: pd.DataFrame):
        # Determine bnd points from reference overland model
        gdf_locs = self._read_waterlevel_boundary_locations()

        if len(df_ts.columns) == 1:
            # Go from 1 timeseries to timeseries for all boundary points
            name = df_ts.columns[0]
            for i in range(1, len(gdf_locs)):
                df_ts[i + 1] = df_ts[name]
            df_ts.columns = list(range(1, len(gdf_locs) + 1))

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
        self._model.setup_pressure_forcing_from_grid(press=ds)

    def _add_bzs_from_bca(
        self, event: IEvent, physical_projection: PhysicalProjectionModel
    ):
        # ONLY offshore models
        """Convert tidal constituents from bca file to waterlevel timeseries that can be read in by hydromt_sfincs."""
        sb = SfincsBoundary()
        sb.read_flow_boundary_points(self.get_model_root() / "sfincs.bnd")
        sb.read_astro_boundary_conditions(self.get_model_root() / "sfincs.bca")

        times = pd.date_range(
            start=event.attrs.time.start_time,
            end=event.attrs.time.end_time,
            freq="10T",
        )

        # Predict tidal signal and add SLR
        if not sb.flow_boundary_points:
            raise ValueError("No flow boundary points found.")

        for bnd_ii in range(len(sb.flow_boundary_points)):
            tide_ii = (
                predict(sb.flow_boundary_points[bnd_ii].astro, times)
                + event.attrs.water_level_offset.convert(us.UnitTypesLength.meters)
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

    def _add_forcing_spw(self, spw_path: Path):
        """Add spiderweb forcing to the sfincs model."""
        if spw_path is None:
            raise ValueError("No path to rainfall track file provided.")

        if not spw_path.exists():
            raise FileNotFoundError(f"SPW file not found: {spw_path}")

        sim_path = self.get_model_root()

        # prevent SameFileError
        if spw_path != sim_path / spw_path.name:
            shutil.copy2(spw_path, sim_path / spw_path.name)

        self._model.set_config("spwfile", spw_path.name)

    ### PRIVATE GETTERS ###
    def _get_result_path(self, scenario: IScenario) -> Path:
        """Return the path to store the results."""
        return self.database.scenarios.output_path / scenario.attrs.name / "Flooding"

    def _get_simulation_paths(self, scenario: IScenario) -> List[Path]:
        base_path = (
            self._get_result_path(scenario)
            / "simulations"
            / self.site.attrs.sfincs.config.overland_model
        )

        if isinstance(scenario.event, EventSet):
            return [
                base_path.parent / sub_event.attrs.name / base_path.name
                for sub_event in scenario.event.events
            ]
        elif isinstance(scenario.event, IEvent):
            return [base_path]
        else:
            raise ValueError(f"Unsupported mode: {scenario.event.attrs.mode}")

    def _get_simulation_path_offshore(self, scenario: IScenario) -> List[Path]:
        # Get the path to the offshore model (will not be used if offshore model is not created)
        if self.site.attrs.sfincs.offshore_model is None:
            raise ValueError("No offshore model found in site.toml.")
        base_path = (
            self._get_result_path(scenario)
            / "simulations"
            / self.site.attrs.sfincs.config.offshore_model
        )
        if isinstance(scenario.event, EventSet):
            return [
                base_path.parent / sub_event.attrs.name / base_path.name
                for sub_event in scenario.event.events
            ]
        elif isinstance(scenario.event, IEvent):
            return [base_path]
        else:
            raise ValueError(f"Unsupported mode: {scenario.event.attrs.mode}")

    def _get_flood_map_paths(self, scenario: IScenario) -> list[Path]:
        """Return the paths to the flood maps that running this scenario should produce."""
        results_path = self._get_result_path(scenario)

        if isinstance(scenario.event, EventSet):
            map_fn = []
            for rp in self.site.attrs.risk.return_periods:
                map_fn.append(results_path / f"RP_{rp:04d}_maps.nc")
        elif isinstance(scenario.event, IEvent):
            map_fn = [results_path / "max_water_level_map.nc"]
        else:
            raise ValueError(f"Unsupported mode: {scenario.event.attrs.mode}")

        return map_fn

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
        df = pd.DataFrame(index=pd.DatetimeIndex(da.time), data=da.to_numpy())

        names = []
        descriptions = []
        # get station names from site.toml
        if self.site.attrs.sfincs.obs_point is not None:
            obs_points = self.site.attrs.sfincs.obs_point
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

    # @gundula do we keep this func, its not used anywhere?
    def _downscale_hmax(self, zsmax, demfile: Path):
        # read DEM and convert units to metric units used by SFINCS
        demfile_units = self.site.attrs.sfincs.dem.units
        dem_conversion = us.UnitfulLength(value=1.0, units=demfile_units).convert(
            us.UnitTypesLength("meters")
        )
        dem = dem_conversion * self._model.data_catalog.get_rasterdataset(demfile)

        # determine conversion factor for output floodmap
        floodmap_units = self.site.attrs.sfincs.floodmap_units
        floodmap_conversion = us.UnitfulLength(
            value=1.0, units=us.UnitTypesLength("meters")
        ).convert(floodmap_units)

        hmax = utils.downscale_floodmap(
            zsmax=floodmap_conversion * zsmax,
            dep=floodmap_conversion * dem,
            hmin=0.01,
        )
        return hmax

    def _read_river_locations(self) -> gpd.GeoDataFrame:
        path = self.get_model_root() / "sfincs.src"

        with open(path) as f:
            lines = f.readlines()
        coords = [(float(line.split()[0]), float(line.split()[1])) for line in lines]
        points = [shapely.Point(coord) for coord in coords]

        return gpd.GeoDataFrame({"geometry": points}, crs=self._model.crs)

    def _read_waterlevel_boundary_locations(self) -> gpd.GeoDataFrame:
        with open(self.get_model_root() / "sfincs.bnd") as f:
            lines = f.readlines()
        coords = [(float(line.split()[0]), float(line.split()[1])) for line in lines]
        points = [shapely.Point(coord) for coord in coords]

        return gpd.GeoDataFrame({"geometry": points}, crs=self._model.crs)
