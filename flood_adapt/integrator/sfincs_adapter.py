import gc
import os
import shutil
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

import flood_adapt.object_model.io.unitfulvalue as uv
from flood_adapt.integrator.interface.hazard_adapter import IHazardAdapter
from flood_adapt.misc.config import Settings
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.object_model.hazard.event.event_factory import EventFactory
from flood_adapt.object_model.hazard.event.event_set import EventSet
from flood_adapt.object_model.hazard.event.forcing.discharge import (
    DischargeConstant,
    DischargeCSV,
    DischargeSynthetic,
)
from flood_adapt.object_model.hazard.event.forcing.rainfall import (
    RainfallConstant,
    RainfallMeteo,
    RainfallSynthetic,
    RainfallTrack,
)
from flood_adapt.object_model.hazard.event.forcing.waterlevels import (
    WaterlevelCSV,
    WaterlevelGauged,
    WaterlevelModel,
    WaterlevelSynthetic,
)
from flood_adapt.object_model.hazard.event.forcing.wind import (
    WindConstant,
    WindMeteo,
    WindSynthetic,
    WindTrack,
)
from flood_adapt.object_model.hazard.event.historical import HistoricalEvent
from flood_adapt.object_model.hazard.event.tide_gauge import TideGauge
from flood_adapt.object_model.hazard.interface.forcing import (
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
from flood_adapt.object_model.hazard.measure.pump import Pump
from flood_adapt.object_model.interface.events import IEvent, IEventModel
from flood_adapt.object_model.interface.measures import HazardMeasure
from flood_adapt.object_model.interface.path_builder import (
    ObjectDir,
    TopLevelDir,
    db_path,
)
from flood_adapt.object_model.interface.projections import (
    PhysicalProjection,
    PhysicalProjectionModel,
)
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.interface.site import Site
from flood_adapt.object_model.projection import Projection
from flood_adapt.object_model.utils import cd, resolve_filepath


class SfincsAdapter(IHazardAdapter):
    _site: Site
    _model: SfincsModel

    ###############
    ### PUBLIC ####
    ###############

    ### HAZARD ADAPTER METHODS ###
    def __init__(self, model_root: str):
        """Load overland sfincs model based on a root directory.

        Args:
            model_root (str): Root directory of overland sfincs model.
        """
        self._site = self.database.site
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
        return self.run_completed()

    def read(self, path: Path):
        """Read the sfincs model from the current model root."""
        if Path(self._model.root) != Path(path):
            self._model.set_root(root=str(path), mode="r")
        self._model.read()

    def write(self, path_out: Union[str, os.PathLike], overwrite: bool = True):
        """Write the sfincs model configuration to a directory."""
        if not isinstance(path_out, Path):
            path_out = Path(path_out)

        if not path_out.exists():
            path_out.mkdir(parents=True)

        write_mode = "w+" if overwrite else "w"
        with cd(path_out):
            self._model.set_root(root=str(path_out), mode=write_mode)
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
        sim_path = sim_path or Path(self._model.root)

        with cd(sim_path):
            sfincs_log = "sfincs.log"
            with FloodAdaptLogging.to_file(file_path=sfincs_log):
                self.logger.info(f"Running SFINCS in {sim_path}...")
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
            self._setup_objects(scenario)

            self.preprocess()
            self.process()
            self.postprocess()

        finally:
            self._cleanup_objects()

    def preprocess(self):
        sim_paths = self._get_simulation_paths()
        if isinstance(self._event, EventSet):
            for sub_event, sim_path in zip(self._event.events, sim_paths):
                self._preprocess_single_event(sub_event, output_path=sim_path)
        elif isinstance(self._event, IEvent):
            self._preprocess_single_event(self._event, output_path=sim_paths[0])

    def process(self):
        if isinstance(self._event, IEvent):
            sim_path = self._get_simulation_paths()[0]
            self.execute(sim_path)

        elif isinstance(self._event, EventSet):
            sim_paths = self._get_simulation_paths()
            for sim_path in sim_paths:
                self.execute(sim_path)

                # postprocess subevents
                self.write_floodmap_geotiff(sim_path=sim_path)
                self.plot_wl_obs(sim_path=sim_path)
                self.write_water_level_map(sim_path=sim_path)

    def postprocess(self):
        if not self.sfincs_completed():
            raise RuntimeError("SFINCS was not run successfully!")

        if isinstance(self._event, IEvent):
            self.write_floodmap_geotiff()
            self.plot_wl_obs()
            self.write_water_level_map()

        elif isinstance(self._event, EventSet):
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

    def add_measure(self, measure: HazardMeasure):
        """Get measure data and add it to the sfincs model."""
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

    def add_projection(self, projection: Projection | PhysicalProjection):
        """Get forcing data currently in the sfincs model and add the projection it."""
        if not isinstance(projection, PhysicalProjection):
            projection = projection.get_physical_projection()

        if projection.attrs.sea_level_rise:
            self.logger.info("Adding sea level rise to model.")
            self.waterlevels += projection.attrs.sea_level_rise.convert(
                uv.UnitTypesLength.meters
            )

        # projection.attrs.subsidence

        if projection.attrs.rainfall_multiplier:
            self.logger.info("Adding rainfall multiplier to model.")
            if self.rainfall is not None:
                self.rainfall *= projection.attrs.rainfall_multiplier
            else:
                self.logger.warning(
                    "Failed to add rainfall multiplier, no rainfall forcing found in the model."
                )

    ### GETTERS ###
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
    def waterlevels(self) -> xr.Dataset | xr.DataArray:
        return self._model.forcing["bzs"]

    @waterlevels.setter
    def waterlevels(self, waterlevels: xr.Dataset | xr.DataArray):
        if self.waterlevels is None or self.waterlevels.size == 0:
            raise ValueError("No water level forcing found in the model.")
        self._model.forcing["bzs"] = waterlevels

    @property
    def discharge(self) -> xr.Dataset | xr.DataArray:
        return self._model.forcing["dis"]

    @discharge.setter
    def discharge(self, discharge: xr.Dataset | xr.DataArray):
        if self.discharge is None or self.discharge.size == 0:
            raise ValueError("No discharge forcing found in the model.")
        self._model.forcing["dis"] = discharge

    @property
    def rainfall(self) -> xr.Dataset | xr.DataArray | None:
        if "precip_2d" in self._model.forcing and "precip" in self._model.forcing:
            raise ValueError("Multiple rainfall forcings found in the model.")

        if "precip_2d" in self._model.forcing:
            return self._model.forcing["precip_2d"]
        elif "precip" in self._model.forcing:
            return self._model.forcing["precip"]
        else:
            return None

    @rainfall.setter
    def rainfall(self, rainfall: xr.Dataset | xr.DataArray):
        if self.rainfall is None or self.rainfall.size == 0:
            raise ValueError("No rainfall forcing found in the model.")

        elif "precip_2d" in self._model.forcing:
            self._model.forcing["precip_2d"] = rainfall
        elif "precip" in self._model.forcing:
            self._model.forcing["precip"] = rainfall

    @property
    def wind(self) -> xr.Dataset | xr.DataArray | None:
        if "wind_2d" in self._model.forcing and "wind" in self._model.forcing:
            raise ValueError("Multiple wind forcings found in the model.")

        if "wind_2d" in self._model.forcing:
            return self._model.forcing["wind_2d"]
        elif "wind" in self._model.forcing:
            return self._model.forcing["wind"]
        else:
            return None

    @wind.setter
    def wind(self, wind: xr.Dataset | xr.DataArray):
        if not self.wind or self.wind.size == 0:
            raise ValueError("No wind forcing found in the model.")

        elif "wind_2d" in self._model.forcing:
            self._model.forcing["wind_2d"] = wind
        elif "wind" in self._model.forcing:
            self._model.forcing["wind"] = wind

    ### OUTPUT ###
    def run_completed(self) -> bool:
        """Check if the entire model run has been completed successfully by checking if all flood maps exist that are created in postprocess().

        Returns
        -------
        bool
            _description_
        """
        any_floodmap = len(self._get_flood_map_paths()) > 0
        all_exist = all(floodmap.exists() for floodmap in self._get_flood_map_paths())
        return any_floodmap and all_exist

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

    def write_floodmap_geotiff(self, sim_path: Path = None):
        results_path = self._get_result_path()
        sim_path = sim_path or self._get_simulation_paths()[0]

        # read SFINCS model
        with SfincsAdapter(model_root=sim_path) as model:
            # dem file for high resolution flood depth map
            demfile = (
                db_path(TopLevelDir.static) / "dem" / self._site.attrs.dem.filename
            )

            # read max. water level
            zsmax = model._get_zsmax()

            # writing the geotiff to the scenario results folder
            model.write_geotiff(
                zsmax,
                demfile=demfile,
                floodmap_fn=results_path / f"FloodMap_{self._scenario.attrs.name}.tif",
            )

    def write_water_level_map(self, sim_path: Path = None):
        """Read simulation results from SFINCS and saves a netcdf with the maximum water levels."""
        results_path = self._get_result_path()
        sim_paths = [sim_path] if sim_path else self._get_simulation_paths()
        # Why only 1 model?
        with SfincsAdapter(model_root=sim_paths[0]) as model:
            zsmax = model._get_zsmax()
            zsmax.to_netcdf(results_path / "max_water_level_map.nc")

    def write_geotiff(self, zsmax, demfile: Path, floodmap_fn: Path):
        # read DEM and convert units to metric units used by SFINCS

        demfile_units = self._site.attrs.dem.units
        dem_conversion = uv.UnitfulLength(value=1.0, units=demfile_units).convert(
            uv.UnitTypesLength("meters")
        )
        dem = dem_conversion * self._model.data_catalog.get_rasterdataset(demfile)

        # determine conversion factor for output floodmap
        floodmap_units = self._site.attrs.sfincs.floodmap_units
        floodmap_conversion = uv.UnitfulLength(
            value=1.0, units=uv.UnitTypesLength("meters")
        ).convert(floodmap_units)

        utils.downscale_floodmap(
            zsmax=floodmap_conversion * zsmax,
            dep=floodmap_conversion * dem,
            hmin=0.01,
            floodmap_fn=str(floodmap_fn),
        )

    def plot_wl_obs(self, sim_path: Path = None):
        """Plot water levels at SFINCS observation points as html.

        Only for single event scenarios, or for a specific simulation path containing the written and processed sfincs model.
        """
        event = EventFactory.load_file(
            db_path(object_dir=ObjectDir.event, obj_name=self._scenario.attrs.event)
            / f"{self._scenario.attrs.event}.toml"
        )

        if sim_path is None:
            if event.attrs.mode != Mode.single_event:
                raise ValueError(
                    "This function is only available for single event scenarios."
                )

        sim_path = sim_path or self._get_simulation_paths()[0]
        # read SFINCS model
        with SfincsAdapter(model_root=sim_path) as model:
            df, gdf = model._get_zs_points()

        gui_units = uv.UnitTypesLength(self._site.attrs.gui.default_length_units)
        conversion_factor = uv.UnitfulLength(
            value=1.0, units=uv.UnitTypesLength("meters")
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
                annotation_text=self._site.attrs.water_level.msl.name,
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
                    units=uv.UnitTypesLength(gui_units),
                )

                if df_gauge is not None:
                    waterlevel = df_gauge.iloc[
                        :, 0
                    ] + self._site.attrs.water_level.msl.height.convert(gui_units)

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

    def add_obs_points(self):
        """Add observation points provided in the site toml to SFINCS model."""
        if self._site.attrs.obs_point is not None:
            self.logger.info("Adding observation points to the overland flood model...")

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
    def calculate_rp_floodmaps(self):
        """Calculate flood risk maps from a set of (currently) SFINCS water level outputs using linear interpolation.

        It would be nice to make it more widely applicable and move the loading of the SFINCS results to self.postprocess_sfincs().

        generates return period water level maps in netcdf format to be used by FIAT
        generates return period water depth maps in geotiff format as product for users

        TODO: make this robust and more efficient for bigger datasets.
        """
        eventset = EventFactory.load_file(
            db_path(object_dir=ObjectDir.event, obj_name=self._scenario.attrs.event)
            / f"{self._scenario.attrs.event}.toml"
        )
        if eventset.attrs.mode != Mode.risk:
            raise ValueError("This function is only available for risk scenarios.")

        result_path = self._get_result_path()
        sim_paths = self._get_simulation_paths()

        phys_proj = Projection.load_file(
            db_path(
                object_dir=ObjectDir.projection,
                obj_name=self._scenario.attrs.projection,
            )
            / f"{self._scenario.attrs.projection}.toml"
        ).get_physical_projection()

        floodmap_rp = self._site.attrs.risk.return_periods
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
                db_path(TopLevelDir.static) / "dem" / self._site.attrs.dem.filename
            )

            # writing the geotiff to the scenario results folder
            with SfincsAdapter(model_root=str(sim_paths[0])) as dummymodel:
                dummymodel.write_geotiff(
                    zs_rp_single.to_array().squeeze().transpose(),
                    demfile=demfile,
                    floodmap_fn=result_path / f"RP_{rp:04d}_maps.tif",
                )

    ######################################
    ### PRIVATE - use at your own risk ###
    ######################################
    def _setup_objects(self, scenario: IScenario):
        self._scenario = scenario
        self._event = scenario.get_event()
        self._projection = scenario.get_projection()
        self._strategy = scenario.get_strategy()

    def _cleanup_objects(self):
        del self._scenario
        del self._event
        del self._projection
        del self._strategy

    def _preprocess_single_event(self, event: IEvent, output_path: Path):
        self.set_timing(event.attrs.time)
        self._sim_path = output_path

        # run offshore model or download wl data,
        # copy required files to the simulation folder (or folders for event sets)
        if self._scenario is None:
            raise ValueError(
                "No scenario loaded for preprocessing. Run _setup_objects() first."
            )

        for forcing in event.get_forcings():
            self.add_forcing(forcing)

        for measure in self._strategy.get_hazard_strategy().measures:
            self.add_measure(measure)

        self.add_projection(self._projection.get_physical_projection())
        self.add_obs_points()

        self.write(path_out=output_path)

    ### FORCING ###
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
        self.logger.info("Adding wind to the overland flood model...")

        if isinstance(forcing, WindConstant):
            # HydroMT function: set wind forcing from constant magnitude and direction
            self._model.setup_wind_forcing(
                timeseries=None,
                magnitude=forcing.speed.convert(uv.UnitTypesVelocity.mps),
                direction=forcing.direction.value,
            )
        elif isinstance(forcing, WindSynthetic):
            tmp_path = Path(tempfile.gettempdir()) / "wind.csv"
            forcing.get_data(t0=t0, t1=t1).to_csv(tmp_path)

            # HydroMT function: set wind forcing from timeseries
            self._model.setup_wind_forcing(
                timeseries=tmp_path, magnitude=None, direction=None
            )
        elif isinstance(forcing, WindMeteo):
            ds = forcing.get_data(t0, t1)

            if ds["lon"].min() > 180:
                ds["lon"] = ds["lon"] - 360

            # HydroMT function: set wind forcing from grid
            self._model.setup_wind_forcing_from_grid(wind=ds)
        elif isinstance(forcing, WindTrack):
            self._add_forcing_spw(forcing.path)
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
        self.logger.info("Adding rainfall to the overland flood model...")

        t0, t1 = self._model.get_model_time()
        if isinstance(forcing, RainfallConstant):
            self._model.setup_precip_forcing(
                timeseries=None,
                magnitude=forcing.intensity.convert(uv.UnitTypesIntensity.mm_hr),
            )
        elif isinstance(forcing, RainfallSynthetic):
            tmp_path = Path(tempfile.gettempdir()) / "precip.csv"
            forcing.get_data(t0=t0, t1=t1).to_csv(tmp_path)
            self._model.setup_precip_forcing(timeseries=tmp_path)
        elif isinstance(forcing, RainfallMeteo):
            ds = forcing.get_data(t0=t0, t1=t1)

            if ds["lon"].min() > 180:
                ds["lon"] = ds["lon"] - 360

            self._model.setup_precip_forcing_from_grid(
                precip=ds["precip"], aggregate=False
            )
        elif isinstance(forcing, RainfallTrack):
            self._add_forcing_spw(forcing.path)
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
        self.logger.info("Adding discharge to the overland flood model...")

        if isinstance(forcing, (DischargeConstant, DischargeCSV, DischargeSynthetic)):
            self._set_single_river_forcing(discharge=forcing)
        else:
            self.logger.warning(
                f"Unsupported discharge forcing type: {forcing.__class__.__name__}"
            )

    def _add_forcing_waterlevels(self, forcing: IWaterlevel):
        t0, t1 = self._model.get_model_time()
        self.logger.info("Adding waterlevels to the overland flood model...")

        if isinstance(
            forcing,
            (WaterlevelSynthetic, WaterlevelCSV, WaterlevelGauged),
        ):
            if (df_ts := forcing.get_data(t0=t0, t1=t1)) is None:
                raise ValueError("Failed to get waterlevel data.")
            self._set_waterlevel_forcing(df_ts)

        elif isinstance(forcing, WaterlevelModel):
            if (df_ts := forcing.get_data(scenario=self._scenario)) is None:
                raise ValueError("Failed to get waterlevel data.")
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
                    uv.UnitfulLength(
                        value=float(height),
                        units=self._site.attrs.gui.default_length_units,
                    ).convert(uv.UnitTypesLength("meters"))
                )
                for height in gdf_floodwall["z"]
            ]
            gdf_floodwall["z"] = heights
            self.logger.info("Using floodwall height from shape file.")
        except Exception:
            self.logger.warning(
                f"""Could not use height data from file due to missing ""z""-column or missing values therein.\n
                Using uniform height of {floodwall.attrs.elevation.convert(uv.UnitTypesLength("meters"))} meters instead."""
            )
            gdf_floodwall["z"] = floodwall.attrs.elevation.convert(
                uv.UnitTypesLength("meters")
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
            for aggr_dict in self._site.attrs.fiat.aggregation:
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
        volume = green_infrastructure.attrs.volume.convert(uv.UnitTypesVolume("m3"))
        volume = green_infrastructure.attrs.volume.convert(uv.UnitTypesVolume("m3"))

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
            discharge=pump.attrs.discharge.convert(uv.UnitTypesDischarge("m3/s")),
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
        model_rivers = self.discharge.vector.to_gdf()

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

    def _turn_off_bnd_press_correction(self):
        """Turn off the boundary pressure correction in the sfincs model."""
        self._model.set_config("pavbnd", -9999)

    def _set_waterlevel_forcing(self, df_ts: pd.DataFrame):
        # Determine bnd points from reference overland model
        gdf_locs = self.waterlevels.vector.to_gdf()
        gdf_locs.crs = self._model.crs

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
        if not sb.flow_boundary_points:
            raise ValueError("No flow boundary points found.")

        for bnd_ii in range(len(sb.flow_boundary_points)):
            tide_ii = (
                predict(sb.flow_boundary_points[bnd_ii].astro, times)
                + event.water_level_offset.convert(uv.UnitTypesLength("meters"))
                + physical_projection.sea_level_rise.convert(
                    uv.UnitTypesLength("meters")
                )
            )

            if bnd_ii == 0:
                wl_df = pd.DataFrame(data={1: tide_ii}, index=times)
            else:
                wl_df[bnd_ii + 1] = tide_ii

        # Determine bnd points from reference overland model
        gdf_locs = self.waterlevels.vector.to_gdf()
        gdf_locs.crs = self._model.crs

        # HydroMT function: set waterlevel forcing from time series
        self._model.set_forcing_1d(
            name="bzs", df_ts=wl_df, gdf_locs=gdf_locs, merge=False
        )

    def _add_forcing_spw(self, spw_path: Path):
        """Add spiderweb forcing to the sfincs model."""
        if not spw_path.exists():
            raise FileNotFoundError(f"SPW file not found: {spw_path}")
        self._sim_path.mkdir(parents=True, exist_ok=True)

        # prevent SameFileError
        if spw_path != self._sim_path / spw_path.name:
            shutil.copy2(spw_path, self._sim_path)

        self._model.set_config("spwfile", spw_path.name)

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
        return (
            db_path(
                top_level_dir=TopLevelDir.output,
                object_dir=ObjectDir.scenario,
                obj_name=scenario_name,
            )
            / "Flooding"
        )

    def _get_simulation_paths(self) -> List[Path]:
        base_path = (
            self._get_result_path()
            / "simulations"
            / self._site.attrs.sfincs.overland_model
        )

        if self._event.attrs.mode == Mode.single_event:
            return [base_path]
        elif self._event.attrs.mode == Mode.risk:
            return [
                base_path.parent / sub_event.attrs.name / base_path.name
                for sub_event in self._event.events
            ]
        else:
            raise ValueError(f"Unsupported mode: {self._event.attrs.mode}")

    def _get_simulation_path_offshore(self) -> List[Path]:
        # Get the path to the offshore model (will not be used if offshore model is not created)
        base_path = (
            self._get_result_path()
            / "simulations"
            / self._site.attrs.sfincs.offshore_model
        )

        if self._event.attrs.mode == Mode.single_event:
            return [base_path]
        elif self._event.attrs.mode == Mode.risk:
            return [
                base_path.parent / sub_event.attrs.name / base_path.name
                for sub_event in self._event.events
            ]
        else:
            raise ValueError(f"Unsupported mode: {self._event.attrs.mode}")

    def _get_flood_map_paths(self) -> list[Path]:
        """_summary_."""
        results_path = self._get_result_path()

        if self._event.attrs.mode == Mode.single_event:
            map_fn = [results_path / "max_water_level_map.nc"]

        elif self._event.attrs.mode == Mode.risk:
            map_fn = []
            for rp in self._site.attrs.risk.return_periods:
                map_fn.append(results_path / f"RP_{rp:04d}_maps.nc")
        else:
            raise ValueError(f"Unsupported mode: {self._event.attrs.mode}")

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
        df = pd.DataFrame(index=pd.DatetimeIndex(da.time), data=da.values)

        names = []
        descriptions = []
        # get station names from site.toml
        if self._site.attrs.obs_point is not None:
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

    # @gundula do we keep this func, its not used anywhere?
    def _downscale_hmax(self, zsmax, demfile: Path):
        # read DEM and convert units to metric units used by SFINCS
        demfile_units = self._site.attrs.dem.units
        dem_conversion = uv.UnitfulLength(value=1.0, units=demfile_units).convert(
            uv.UnitTypesLength("meters")
        )
        dem = dem_conversion * self._model.data_catalog.get_rasterdataset(demfile)

        # determine conversion factor for output floodmap
        floodmap_units = self._site.attrs.sfincs.floodmap_units
        floodmap_conversion = uv.UnitfulLength(
            value=1.0, units=uv.UnitTypesLength("meters")
        ).convert(floodmap_units)

        hmax = utils.downscale_floodmap(
            zsmax=floodmap_conversion * zsmax,
            dep=floodmap_conversion * dem,
            hmin=0.01,
        )
        return hmax
