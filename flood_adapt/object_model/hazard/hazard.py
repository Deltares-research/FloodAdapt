import os
import shutil
import subprocess
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import xarray as xr
from noaa_coops.station import COOPSAPIError
from numpy import matlib

import flood_adapt.config as FloodAdapt_config
from flood_adapt.integrator.sfincs_adapter import SfincsAdapter
from flood_adapt.log import FloodAdaptLogging
from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.hazard.event.event_factory import EventFactory
from flood_adapt.object_model.hazard.event.eventset import EventSet
from flood_adapt.object_model.hazard.event.historical_nearshore import (
    HistoricalNearshore,
)
from flood_adapt.object_model.hazard.hazard_strategy import HazardStrategy
from flood_adapt.object_model.hazard.physical_projection import PhysicalProjection
from flood_adapt.object_model.interface.events import Mode
from flood_adapt.object_model.interface.scenarios import ScenarioModel
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDischarge,
    UnitfulIntensity,
    UnitfulLength,
    UnitfulVelocity,
    UnitTypesDischarge,
    UnitTypesIntensity,
    UnitTypesLength,
    UnitTypesVelocity,
)
from flood_adapt.object_model.utils import cd


class Hazard:
    """All information related to the hazard of the scenario.

    Includes functions to generate generic timeseries for the hazard models
    and to run the hazard models.
    """

    name: str
    database_input_path: Path
    mode: Mode
    event_set: EventSet
    physical_projection: PhysicalProjection
    hazard_strategy: HazardStrategy
    has_run: bool = False

    def __init__(self, scenario: ScenarioModel, database, results_dir: Path) -> None:
        self._logger = FloodAdaptLogging.getLogger(__name__)

        self._mode: Mode
        self.simulation_paths: List[Path]
        self.simulation_paths_offshore: List[Path]
        self.name = scenario.name
        self.results_dir = results_dir
        self.database = database
        self.event_name = scenario.event
        self.set_event()  # also setting the mode (single_event or risk here)
        self.set_hazard_strategy(scenario.strategy)
        self.set_physical_projection(scenario.projection)
        self.site = database.site
        self.has_run = self.has_run_check()

    @property
    def event_mode(self) -> Mode:
        return self._mode

    @event_mode.setter
    def event_mode(self, mode: Mode) -> None:
        self._mode = mode

    def set_simulation_paths(self) -> None:
        if self._mode == Mode.single_event:
            self.simulation_paths = [
                self.database.scenarios.get_database_path(
                    get_input_path=False
                ).joinpath(
                    self.name,
                    "Flooding",
                    "simulations",
                    self.site.attrs.sfincs.overland_model,
                )
            ]
            # Create a folder name for the offshore model (will not be used if offshore model is not created)
            if self.site.attrs.sfincs.offshore_model is not None:
                self.simulation_paths_offshore = [
                    self.database.scenarios.get_database_path(
                        get_input_path=False
                    ).joinpath(
                        self.name,
                        "Flooding",
                        "simulations",
                        self.site.attrs.sfincs.offshore_model,
                    )
                ]
        elif self._mode == Mode.risk:  # risk mode requires an additional folder layer
            self.simulation_paths = []
            self.simulation_paths_offshore = []
            for subevent in self.event_list:
                self.simulation_paths.append(
                    self.database.scenarios.get_database_path(
                        get_input_path=False
                    ).joinpath(
                        self.name,
                        "Flooding",
                        "simulations",
                        subevent.attrs.name,
                        self.site.attrs.sfincs.overland_model,
                    )
                )
                # Create a folder name for the offshore model (will not be used if offshore model is not created)
                if self.site.attrs.sfincs.offshore_model is not None:
                    self.simulation_paths_offshore.append(
                        self.database.scenarios.get_database_path(
                            get_input_path=False
                        ).joinpath(
                            self.name,
                            "Flooding",
                            "simulations",
                            subevent.attrs.name,
                            self.site.attrs.sfincs.offshore_model,
                        )
                    )

    def has_run_check(self) -> bool:
        """_summary_.

        Returns
        -------
        bool
            _description_
        """
        self._get_flood_map_path()

        # Iterate to all needed flood map files to check if they exists
        checks = []
        for map in self.flood_map_path:
            checks.append(map.exists())

        return all(checks)

    def sfincs_has_run_check(self) -> bool:
        """Check if the hazard has been already run."""
        test_combined = False
        if len(self.simulation_paths) == 0:
            raise ValueError("The Scenario has not been initialized correctly.")
        else:
            test1 = False
            test2 = False
            for sfincs_path in self.simulation_paths:
                if sfincs_path.exists():
                    for fname in os.listdir(sfincs_path):
                        if fname.endswith("_map.nc"):
                            test1 = True
                            break

                sfincs_log = sfincs_path.joinpath("sfincs.log")

                if sfincs_log.exists():
                    with open(sfincs_log) as myfile:
                        if "Simulation finished" in myfile.read():
                            test2 = True

            test_combined = (test1) & (test2)
        return test_combined

    def set_event(self) -> None:
        """Set the actual Event template class list using the list of measure names.

        Args:
            event_name (str): name of event used in scenario.
        """
        self.event_set_path = (
            self.database.events.get_database_path()
            / self.event_name
            / f"{self.event_name}.toml"
        )
        # set mode (probabilistic_set or single_event)
        self.event_mode = Event.get_mode(self.event_set_path)
        self.event_set = EventSet.load_file(self.event_set_path)

    def _set_event_objects(self) -> None:
        if self._mode == Mode.single_event:
            self.event_set.event_paths = [self.event_set_path]
            self.probabilities = [1]

        elif self._mode == Mode.risk:
            self.event_set.event_paths = []
            subevents = self.event_set.attrs.subevent_name

            for subevent in subevents:
                event_path = (
                    self.database.events.get_database_path()
                    / self.event_name
                    / subevent
                    / f"{subevent}.toml"
                )
                self.event_set.event_paths.append(event_path)

        # parse event config file to get event template
        self.event_list = []
        for event_path in self.event_set.event_paths:
            template = Event.get_template(event_path)
            # use event template to get the associated event child class
            self.event_list.append(
                EventFactory.get_event(template).load_file(event_path)
            )
            self.event = self.event_list[
                0
            ]  # set event for single_event to be able to plot wl etc

    def set_physical_projection(self, projection: str) -> None:
        self.physical_projection = self.database.projections.get(
            projection
        ).get_physical_projection()

    def set_hazard_strategy(self, strategy: str) -> None:
        self.hazard_strategy = self.database.strategies.get(
            strategy
        ).get_hazard_strategy()

    # no write function is needed since this is only used internally

    def preprocess_models(self):
        self._logger.info("Preparing hazard models...")
        # Preprocess all hazard model input
        self.preprocess_sfincs()
        # add other models here

    def run_models(self):
        for parent in reversed(self.results_dir.parents):
            if not parent.exists():
                os.mkdir(parent)
        if not self.results_dir.exists():
            os.mkdir(self.results_dir)
        self._logger.info("Running hazard models...")
        if not self.has_run:
            self.run_sfincs()

    def postprocess_models(self):
        self._logger.info("Post-processing hazard models...")
        # Postprocess all hazard model input
        self.postprocess_sfincs()
        # add other models here
        # remove simulation folders
        if not self.site.attrs.sfincs.save_simulation:
            sim_path = self.results_dir.joinpath("simulations")
            if os.path.exists(sim_path):
                try:
                    shutil.rmtree(sim_path)
                except OSError as e_info:
                    self._logger.warning(f"{e_info}\nCould not delete {sim_path}.")

    def run_sfincs(self):
        # Run new model(s)
        if not FloodAdapt_config.get_system_folder():
            raise ValueError(
                """
                SYSTEM_FOLDER environment variable is not set. Set it by calling FloodAdapt_config.set_system_folder() and provide the path.
                The path should be a directory containing folders with the model executables
                """
            )

        sfincs_exec = FloodAdapt_config.get_system_folder() / "sfincs" / "sfincs.exe"

        run_success = True
        for simulation_path in self.simulation_paths:
            with cd(simulation_path):
                sfincs_log = "sfincs.log"
                # with open(results_dir.joinpath(f"{self.name}.log"), "a") as log_handler:
                with open(sfincs_log, "a") as log_handler:
                    return_code = subprocess.run(sfincs_exec, stdout=log_handler)
                    if return_code.returncode != 0:
                        run_success = False
                        break

        if not run_success:
            # Remove all files in the simulation folder except for the log files
            for simulation_path in self.simulation_paths:
                for subdir, _, files in os.walk(simulation_path):
                    for file in files:
                        if not file.endswith(".log"):
                            os.remove(os.path.join(subdir, file))

            # Remove all empty directories in the simulation folder (so only folders with log files remain)
            for simulation_path in self.simulation_paths:
                for subdir, _, files in os.walk(simulation_path):
                    if not files:
                        os.rmdir(subdir)

            raise RuntimeError("SFINCS model failed to run.")

        # Indicator that hazard has run
        self.__setattr__("has_run", True)

    def run_sfincs_offshore(self, ii: int):
        # Run offshore model(s)
        if not FloodAdapt_config.get_system_folder():
            raise ValueError(
                """
                SYSTEM_FOLDER environment variable is not set. Set it by calling FloodAdapt_config.set_system_folder() and provide the path.
                The path should be a directory containing folders with the model executables
                """
            )
        sfincs_exec = FloodAdapt_config.get_system_folder() / "sfincs" / "sfincs.exe"

        simulation_path = self.simulation_paths_offshore[ii]
        with cd(simulation_path):
            sfincs_log = "sfincs.log"
            with open(sfincs_log, "w") as log_handler:
                subprocess.run(sfincs_exec, stdout=log_handler)

    def preprocess_sfincs(
        self,
    ):
        self._set_event_objects()
        self.set_simulation_paths()
        path_in = self.database.static_path.joinpath(
            "templates", self.site.attrs.sfincs.overland_model
        )

        for ii, event in enumerate(self.event_list):
            self.event = event  # set current event to ii-th event in event set
            event_dir = self.event_set.event_paths[ii].parent

            # Check if path_out exists and remove if it does because hydromt does not like if there is already an existing model
            if os.path.exists(self.simulation_paths[ii].parent):
                shutil.rmtree(self.simulation_paths[ii].parent)

            # Load overland sfincs model
            model = SfincsAdapter(model_root=path_in, site=self.site)

            # adjust timing of model
            model.set_timing(self.event.attrs)

            # Download meteo files if necessary
            if (
                self.event.attrs.wind.source == "map"
                or self.event.attrs.rainfall.source == "map"
                or self.event.attrs.template == "Historical_offshore"
            ):
                self._logger.info("Downloading meteo data...")
                meteo_dir = self.database.output_path.joinpath("meteo")
                if not meteo_dir.is_dir():
                    os.mkdir(self.database.output_path.joinpath("meteo"))
                ds = self.event.download_meteo(
                    site=self.site, path=meteo_dir
                )  # =event_dir)
                ds = ds.rename({"barometric_pressure": "press"})
                ds = ds.rename({"precipitation": "precip"})
            else:
                ds = None

            # Generate and change water level boundary condition
            template = self.event.attrs.template

            if template == "Synthetic" or template == "Historical_nearshore":
                # generate hazard water level bc incl SLR (in the offshore model these are already included)
                # returning wl referenced to MSL
                if self.event.attrs.template == "Synthetic":
                    self.event.add_tide_and_surge_ts()
                    # add water level offset due to historic SLR for synthetic event
                    wl_ts = (
                        self.event.tide_surge_ts
                        + self.site.attrs.slr.vertical_offset.convert(
                            self.site.attrs.gui.default_length_units
                        )
                    )
                elif self.event.attrs.template == "Historical_nearshore":
                    # water level offset due to historic SLR already included in observations
                    wl_ts = self.event.tide_surge_ts
                # In both cases (Synthetic and Historical nearshore) add SLR
                wl_ts[1] = wl_ts[
                    1
                ] + self.physical_projection.attrs.sea_level_rise.convert(
                    self.site.attrs.gui.default_length_units
                )
                # unit conversion to metric units (not needed for water levels coming from the offshore model, see below)
                gui_units = UnitfulLength(
                    value=1.0, units=self.site.attrs.gui.default_length_units
                )
                conversion_factor = gui_units.convert(UnitTypesLength("meters"))
                self.wl_ts = conversion_factor * wl_ts
            elif (
                template == "Historical_offshore" or template == "Historical_hurricane"
            ):
                self._logger.info(
                    "Preparing offshore model to generate tide and surge..."
                )
                self.preprocess_sfincs_offshore(ds=ds, ii=ii)
                # Run the actual SFINCS model
                self._logger.info("Running offshore model...")
                self.run_sfincs_offshore(ii=ii)
                # add wl_ts to self
                self.postprocess_sfincs_offshore(ii=ii)

                # turn off pressure correction at the boundaries because the effect of
                # atmospheric pressure is already included in the water levels from the
                # offshore model
                model.turn_off_bnd_press_correction()

            self._logger.info(
                "Adding water level boundary conditions to the overland flood model..."
            )
            # add difference between MSL (vertical datum of offshore nad backend in general) and overland model
            self.wl_ts += self.site.attrs.water_level.msl.height.convert(
                UnitTypesLength("meters")
            ) - self.site.attrs.water_level.localdatum.height.convert(
                UnitTypesLength("meters")
            )
            model.add_wl_bc(self.wl_ts)

            # ASSUMPTION: Order of the rivers is the same as the site.toml file
            if self.site.attrs.river is not None:
                self.event.add_dis_ts(
                    event_dir=event_dir, site_river=self.site.attrs.river
                )
            else:
                self.event.dis_df = None
            if self.event.dis_df is not None:
                # Generate and change discharge boundary condition
                self._logger.info(
                    "Adding discharge boundary conditions if applicable to the overland flood model..."
                )
                # convert to metric units
                gui_units = UnitfulDischarge(
                    value=1.0, units=self.site.attrs.gui.default_discharge_units
                )
                conversion_factor = gui_units.convert(UnitTypesDischarge("m3/s"))
                model.add_dis_bc(
                    list_df=conversion_factor * self.event.dis_df,
                    site_river=self.site.attrs.river,
                )

            # Generate and add rainfall boundary condition
            gui_units_precip = UnitfulIntensity(
                value=1.0, units=self.site.attrs.gui.default_intensity_units
            )
            conversion_factor_precip = gui_units_precip.convert(
                UnitTypesIntensity("mm/hr")
            )
            if self.event.attrs.template != "Historical_hurricane":
                if self.event.attrs.rainfall.source == "map":
                    self._logger.info(
                        "Adding gridded rainfall to the overland flood model..."
                    )
                    # add rainfall increase from projection and event, units area already conform with sfincs when downloaded
                    model.add_precip_forcing_from_grid(
                        ds=ds["precip"]
                        * (1 + self.physical_projection.attrs.rainfall_increase / 100.0)
                        * (1 + self.event.attrs.rainfall.increase / 100.0)
                    )
                elif self.event.attrs.rainfall.source == "timeseries":
                    # convert to metric units
                    df = pd.read_csv(
                        event_dir.joinpath(self.event.attrs.rainfall.timeseries_file),
                        index_col=0,
                        header=None,
                    )
                    df.index = pd.DatetimeIndex(df.index)
                    # add unit conversion and rainfall increase from projection and event
                    df = (
                        conversion_factor_precip
                        * df
                        * (1 + self.physical_projection.attrs.rainfall_increase / 100.0)
                        * (1 + self.event.attrs.rainfall.increase / 100.0)
                    )

                    self._logger.info(
                        "Adding rainfall timeseries to the overland flood model..."
                    )
                    model.add_precip_forcing(timeseries=df)
                elif self.event.attrs.rainfall.source == "constant":
                    self._logger.info(
                        "Adding constant rainfall to the overland flood model..."
                    )
                    # add unit conversion and rainfall increase from projection, not event since the user can adjust constant rainfall accordingly
                    const_precipitation = (
                        self.event.attrs.rainfall.constant_intensity.convert("mm/hr")
                        * (1 + self.physical_projection.attrs.rainfall_increase / 100.0)
                    )
                    model.add_precip_forcing(const_precip=const_precipitation)
                elif self.event.attrs.rainfall.source == "shape":
                    self._logger.info(
                        "Adding rainfall shape timeseries to the overland flood model..."
                    )
                    if self.event.attrs.rainfall.shape_type == "scs":
                        scsfile = self.database.static_path.joinpath(
                            "scs", self.site.attrs.scs.file
                        )
                        scstype = self.site.attrs.scs.type
                        self.event.add_rainfall_ts(scsfile=scsfile, scstype=scstype)
                    else:
                        self.event.add_rainfall_ts()
                    # add unit conversion and rainfall increase from projection, not event since the user can adjust cumulative rainfall accordingly
                    model.add_precip_forcing(
                        timeseries=self.event.rain_ts
                        * conversion_factor_precip
                        * (1 + self.physical_projection.attrs.rainfall_increase / 100.0)
                    )

                # Generate and add wind boundary condition
                # conversion factor to metric units
                gui_units_wind = UnitfulVelocity(
                    value=1.0, units=self.site.attrs.gui.default_velocity_units
                )
                conversion_factor_wind = gui_units_wind.convert(
                    UnitTypesVelocity("m/s")
                )
                # conversion factor to metric units
                gui_units_wind = UnitfulVelocity(
                    value=1.0, units=self.site.attrs.gui.default_velocity_units
                )
                conversion_factor_wind = gui_units_wind.convert(
                    UnitTypesVelocity("m/s")
                )
                if self.event.attrs.wind.source == "map":
                    self._logger.info(
                        "Adding gridded wind field to the overland flood model..."
                    )
                    model.add_wind_forcing_from_grid(ds=ds)
                elif self.event.attrs.wind.source == "timeseries":
                    self._logger.info(
                        "Adding wind timeseries to the overland flood model..."
                    )
                    df = pd.read_csv(
                        event_dir.joinpath(self.event.attrs.wind.timeseries_file),
                        index_col=0,
                        header=None,
                    )
                    df[1] = conversion_factor_precip * df[1]
                    df.index = pd.DatetimeIndex(df.index)
                    model.add_wind_forcing(timeseries=df)
                elif self.event.attrs.wind.source == "constant":
                    self._logger.info(
                        "Adding constant wind to the overland flood model..."
                    )
                    model.add_wind_forcing(
                        const_mag=self.event.attrs.wind.constant_speed.value
                        * conversion_factor_wind,
                        const_dir=self.event.attrs.wind.constant_direction.value,
                    )
            else:
                # Copy spw file also to nearshore folder
                self._logger.info(
                    "Adding wind field generated from hurricane track to the overland flood model..."
                )
                spw_name = "hurricane.spw"
                model.set_config_spw(spw_name=spw_name)
                if self.physical_projection.attrs.rainfall_increase != 0.0:
                    self._logger.warning(
                        "Rainfall increase from projection is not applied to hurricane events where the spatial rainfall is derived from the track variables."
                    )

            # Add hazard measures if included
            if self.hazard_strategy.measures is not None:
                for measure in self.hazard_strategy.measures:
                    measure_path = self.database.measures.get_database_path().joinpath(
                        measure.attrs.name
                    )
                    if measure.attrs.type == "floodwall":
                        self._logger.info(
                            "Adding floodwall to the overland flood model..."
                        )
                        model.add_floodwall(
                            floodwall=measure.attrs, measure_path=measure_path
                        )
                    if measure.attrs.type == "pump":
                        model.add_pump(pump=measure.attrs, measure_path=measure_path)
                    if (
                        measure.attrs.type == "greening"
                        or measure.attrs.type == "total_storage"
                        or measure.attrs.type == "water_square"
                    ):
                        self._logger.info(
                            "Adding green infrastructure to the overland flood model..."
                        )
                        model.add_green_infrastructure(
                            green_infrastructure=measure.attrs,
                            measure_path=measure_path,
                        )

            # add observation points from site.toml
            model.add_obs_points()
            self._logger.info(
                "Adding observation points to the overland flood model..."
            )

            # write sfincs model in output destination
            model.write_sfincs_model(path_out=self.simulation_paths[ii])

            # Write spw file to overland folder
            if self.event.attrs.template == "Historical_hurricane":
                shutil.copy2(
                    self.simulation_paths_offshore[ii].joinpath(spw_name),
                    self.simulation_paths[ii].joinpath(spw_name),
                )

            del model

    def preprocess_sfincs_offshore(self, ds: xr.DataArray, ii: int):
        """Preprocess offshore model to obtain water levels for boundary condition of the nearshore model.

        Args:
            ds (xr.DataArray): DataArray with meteo information (downloaded using event.download_meteo())
            ii (int): Iterator for event set
        """
        if self.site.attrs.sfincs.offshore_model is None:
            raise ValueError(
                f"An offshore model needs to be defined in the site.toml with sfincs.offshore_model to run an event of type '{self.event.attrs.template}'"
            )
        # Determine folders for offshore model
        path_in_offshore = self.database.static_path.joinpath(
            "templates", self.site.attrs.sfincs.offshore_model
        )
        if self.event_mode == Mode.risk:
            event_dir = (
                self.database.events.get_database_path()
                / self.event_set.attrs.name
                / self.event.attrs.name
            )
        else:
            event_dir = self.database.events.get_database_path() / self.event.attrs.name

        # Create folders for offshore model
        self.simulation_paths_offshore[ii].mkdir(parents=True, exist_ok=True)

        # Initiate offshore model
        offshore_model = SfincsAdapter(model_root=path_in_offshore, site=self.site)

        # Set timing of offshore model (same as overland model)
        offshore_model.set_timing(self.event.attrs)

        # set wl of offshore model
        offshore_model.add_bzs_from_bca(
            self.event.attrs, self.physical_projection.attrs
        )

        # Add wind and if applicable pressure forcing from meteo data (historical_offshore) or spiderweb file (historical_hurricane).
        if self.event.attrs.template == "Historical_offshore":
            if self.event.attrs.wind.source == "map":
                offshore_model.add_wind_forcing_from_grid(ds=ds)
                offshore_model.add_pressure_forcing_from_grid(ds=ds["press"])
            elif self.event.attrs.wind.source == "timeseries":
                offshore_model.add_wind_forcing(
                    timeseries=event_dir.joinpath(self.event.attrs.wind.timeseries_file)
                )
            elif self.event.attrs.wind.source == "constant":
                offshore_model.add_wind_forcing(
                    const_mag=self.event.attrs.wind.constant_speed.value,
                    const_dir=self.event.attrs.wind.constant_direction.value,
                )
        elif self.event.attrs.template == "Historical_hurricane":
            spw_name = "hurricane.spw"
            offshore_model.set_config_spw(spw_name=spw_name)
            if event_dir.joinpath(spw_name).is_file():
                self._logger.info("Using existing hurricane meteo data.")
                # copy spw file from event directory to offshore model folder
                shutil.copy2(
                    event_dir.joinpath(spw_name),
                    self.simulation_paths_offshore[ii].joinpath(spw_name),
                )
            else:
                self._logger.info(
                    "Generating meteo input to the model from the hurricane track..."
                )
                offshore_model.add_spw_forcing(
                    historical_hurricane=self.event,
                    database_path=self.database.base_path,
                    model_dir=self.simulation_paths_offshore[ii],
                )
                # save created spw file in the event directory
                shutil.copy2(
                    self.simulation_paths_offshore[ii].joinpath(spw_name),
                    event_dir.joinpath(spw_name),
                )
                self._logger.info(
                    "Finished generating meteo data from hurricane track."
                )

        # write sfincs model in output destination
        offshore_model.write_sfincs_model(path_out=self.simulation_paths_offshore[ii])

        del offshore_model

    def postprocess_sfincs_offshore(self, ii: int):
        # Initiate offshore model
        offshore_model = SfincsAdapter(
            model_root=self.simulation_paths_offshore[ii], site=self.site
        )

        # take the results from offshore model as input for wl bnd
        self.wl_ts = offshore_model.get_wl_df_from_offshore_his_results()

        del offshore_model

    def postprocess_sfincs(self):
        if not self.sfincs_has_run_check():
            raise RuntimeError("SFINCS was not run successfully!")
        if self._mode == Mode.single_event:
            # Write flood-depth map geotiff
            self.write_floodmap_geotiff()
            # Write watel-level time-series
            if self.site.attrs.obs_point is not None:
                self.plot_wl_obs()
            # Write max water-level netcdf
            self.write_water_level_map()
        elif self._mode == Mode.risk:
            # Write max water-level netcdfs per return period
            self.calculate_rp_floodmaps()

        # Save flood map paths in object
        self._get_flood_map_path()

    def _get_flood_map_path(self):
        """_summary_."""
        results_path = self.results_dir
        mode = self.event_mode

        if mode == Mode.single_event:
            map_fn = [results_path.joinpath("max_water_level_map.nc")]

        elif mode == Mode.risk:
            map_fn = []
            for rp in self.site.attrs.risk.return_periods:
                map_fn.append(results_path.joinpath(f"RP_{rp:04d}_maps.nc"))

        self.flood_map_path = map_fn

    def write_water_level_map(self):
        """Read simulation results from SFINCS and saves a netcdf with the maximum water levels."""
        # read SFINCS model
        model = SfincsAdapter(model_root=self.simulation_paths[0], site=self.site)
        zsmax = model.read_zsmax()
        zsmax.to_netcdf(self.results_dir.joinpath("max_water_level_map.nc"))
        del model

    def plot_wl_obs(self):
        """Plot water levels at SFINCS observation points as html.

        Only for single event scenarios.
        """
        for sim_path in self.simulation_paths:
            # read SFINCS model
            model = SfincsAdapter(model_root=sim_path, site=self.site)

            df, gdf = model.read_zs_points()

            del model

            gui_units = UnitTypesLength(self.site.attrs.gui.default_length_units)

            conversion_factor = UnitfulLength(
                value=1.0, units=UnitTypesLength("meters")
            ).convert(gui_units)

            for ii, col in enumerate(df.columns):
                # Plot actual thing
                fig = px.line(
                    df[col] * conversion_factor
                    + self.site.attrs.water_level.localdatum.height.convert(
                        gui_units
                    )  # convert to reference datum for plotting
                )

                # plot reference water levels
                fig.add_hline(
                    y=self.site.attrs.water_level.msl.height.convert(gui_units),
                    line_dash="dash",
                    line_color="#000000",
                    annotation_text="MSL",
                    annotation_position="bottom right",
                )
                if self.site.attrs.water_level.other:
                    for wl_ref in self.site.attrs.water_level.other:
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
                if self.event.attrs.timing == "historical":
                    # check if observation station has a tide gauge ID
                    # if yes to both download tide gauge data and add to plot
                    if (
                        isinstance(self.site.attrs.obs_point[ii].ID, int)
                        or self.site.attrs.obs_point[ii].file is not None
                    ):
                        if self.site.attrs.obs_point[ii].file is not None:
                            file = self.database.static_path.joinpath(
                                self.site.attrs.obs_point[ii].file
                            )
                        else:
                            file = None

                        try:
                            df_gauge = HistoricalNearshore.download_wl_data(
                                station_id=self.site.attrs.obs_point[ii].ID,
                                start_time_str=self.event.attrs.time.start_time,
                                stop_time_str=self.event.attrs.time.end_time,
                                units=UnitTypesLength(gui_units),
                                source=self.site.attrs.tide_gauge.source,
                                file=file,
                            )
                        except (
                            COOPSAPIError
                        ) as e:  # TODO this should be a generic error!
                            self._logger.warning(
                                f"Could not download tide gauge data for station {self.site.attrs.obs_point[ii].ID}. {e}"
                            )
                        else:
                            # If data is available, add to plot
                            fig.add_trace(
                                go.Scatter(
                                    x=pd.DatetimeIndex(df_gauge.index),
                                    y=df_gauge[1]
                                    + self.site.attrs.water_level.msl.height.convert(
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
                fig.write_html(
                    sim_path.parent.parent.joinpath(f"{station_name}_timeseries.html")
                )

    def write_floodmap_geotiff(self):
        # Load overland sfincs model
        for sim_path in self.simulation_paths:
            # read SFINCS model
            model = SfincsAdapter(model_root=sim_path, site=self.site)
            # dem file for high resolution flood depth map
            demfile = self.database.static_path.joinpath(
                "dem", self.site.attrs.dem.filename
            )

            # read max. water level
            zsmax = model.read_zsmax()

            # writing the geotiff to the scenario results folder
            model.write_geotiff(
                zsmax,
                demfile=demfile,
                floodmap_fn=sim_path.parent.parent.joinpath(
                    f"FloodMap_{self.name}.tif"
                ),
            )

            del model

    def __eq__(self, other):
        if not isinstance(other, Hazard):
            # don't attempt to compare against unrelated types
            return NotImplemented
        self._set_event_objects()
        other._set_event_objects()
        test1 = self.event_list == other.event_list
        test2 = self.physical_projection == other.physical_projection
        test3 = self.hazard_strategy == other.hazard_strategy
        return test1 & test2 & test3

    def calculate_rp_floodmaps(self):
        """Calculate flood risk maps from a set of (currently) SFINCS water level outputs using linear interpolation.

        It would be nice to make it more widely applicable and move the loading of the SFINCS results to self.postprocess_sfincs().

        generates return period water level maps in netcdf format to be used by FIAT
        generates return period water depth maps in geotiff format as product for users

        TODO: make this robust and more efficient for bigger datasets.
        """
        floodmap_rp = self.site.attrs.risk.return_periods

        frequencies = self.event_set.attrs.frequency
        # adjust storm frequency for hurricane events
        if self.physical_projection.attrs.storm_frequency_increase != 0:
            storminess_increase = (
                self.physical_projection.attrs.storm_frequency_increase / 100.0
            )
            for ii, event in enumerate(self.event_list):
                if event.attrs.template == "Historical_hurricane":
                    frequencies[ii] = frequencies[ii] * (1 + storminess_increase)

        dummymodel = SfincsAdapter(
            model_root=str(self.simulation_paths[0]), site=self.site
        )
        mask = dummymodel.get_mask().stack(z=("x", "y"))
        zb = dummymodel.get_bedlevel().stack(z=("x", "y")).to_numpy()
        del dummymodel

        zs_maps = []
        for simulation_path in self.simulation_paths:
            # read zsmax data from overland sfincs model
            sim = SfincsAdapter(model_root=str(simulation_path), site=self.site)
            zsmax = sim.read_zsmax().load()
            zs_stacked = zsmax.stack(z=("x", "y"))
            zs_maps.append(zs_stacked)

            del sim

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

        self._logger.info("Calculating flood risk maps, this may take some time...")
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
            fn_rp = self.simulation_paths[0].parent.parent.parent.joinpath(
                f"RP_{rp:04d}_maps.nc"
            )
            zs_rp_single.to_netcdf(fn_rp)

            # write geotiff
            # dem file for high resolution flood depth map
            demfile = self.database.static_path.joinpath(
                "dem", self.site.attrs.dem.filename
            )
            # writing the geotiff to the scenario results folder
            dummymodel = SfincsAdapter(
                model_root=str(self.simulation_paths[0]), site=self.site
            )
            dummymodel.write_geotiff(
                zs_rp_single.to_array().squeeze().transpose(),
                demfile=demfile,
                floodmap_fn=self.simulation_paths[0].parent.parent.parent.joinpath(
                    f"RP_{rp:04d}_maps.tif"
                ),
            )
            del dummymodel

    def calculate_floodfrequency_map(self):
        raise NotImplementedError
        # CFRSS code below

        # # Create Flood frequency map
        # zs_maps = []
        # dem = read_geotiff(config_dict, scenarioDict)
        # freq_dem = np.zeros_like(dem)
        # for ii, zs_max_path in enumerate(results_full_path):
        #     # read zsmax data
        #     fn_dat = zs_max_path.parent.joinpath('sfincs.ind')
        #     data_ind = np.fromfile(fn_dat, dtype="i4")
        #     index = data_ind[1:] - 1  # because python starts counting at 0
        #     fn_dat = zs_max_path
        #     data_zs_orig = np.fromfile(fn_dat, dtype="f4")
        #     data_zs = data_zs_orig[1:int(len(data_zs_orig) / 2) - 1]
        #     da = xr.DataArray(data=data_zs,
        #                     dims=["index"],
        #                     coords=dict(index=(["index"], index)))
        #     zs_maps.append(da) # save for RP map calculation

        #     # create flood depth hmax

        #     nmax = int(sf_input_df.loc['nmax'])
        #     mmax = int(sf_input_df.loc['mmax'])
        #     zsmax = np.zeros(nmax * mmax) - 999.0
        #     zsmax[index] = data_zs
        #     zsmax_dem = resample_sfincs_on_dem(zsmax, config_dict, scenarioDict)
        #     # calculate max. flood depth as difference between water level zs and dem, do not allow for negative values
        #     hmax_dem = zsmax_dem - dem
        #     hmax_dem = np.where(hmax_dem < 0, 0, hmax_dem)

        #     # For every grid cell, take the sum of frequencies for which it was flooded (above threshold). The sresult is frequency of flooding for that grid cell
        #     freq_dem += np.where(hmax_dem > threshold, probability[ii], 0)

        # no_datavalue = float(config_dict['no_data_value'])
        # freq_dem = np.where(np.isnan(hmax_dem), no_datavalue, freq_dem)

        # # write flooding frequency to geotiff
        # demfile = Path(scenarioDict['static_path'], 'dem', config_dict['demfilename'])
        # dem_ds = gdal.Open(str(demfile))
        # [cols, rows] = dem.shape
        # driver = gdal.GetDriverByName("GTiff")
        # fn_tif = str(result_folder.joinpath('Flood_frequency.tif'))
        # outdata = driver.Create(fn_tif, rows, cols, 1, gdal.GDT_Float32)
        # outdata.SetGeoTransform(dem_ds.GetGeoTransform())  ##sets same geotransform as input
        # outdata.SetProjection(dem_ds.GetProjection())  ##sets same projection as input
        # outdata.GetRasterBand(1).WriteArray(freq_dem)
        # outdata.GetRasterBand(1).SetNoDataValue(no_datavalue)  ##if you want these values transparent
        # outdata.SetMetadata({k: str(v) for k, v in scenarioDict.items()})
        # self._logger.info("Created geotiff file with flood frequency.")
        # print("Created geotiff file with flood frequency.", file=sys.stdout, flush=True)

        # outdata.FlushCache()  ##saves to disk!!
        # outdata = None
        # band = None
        # dem_ds = None
