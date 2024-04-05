import logging
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
from numpy import matlib

import flood_adapt.config as FloodAdapt_config
from flood_adapt.integrator.sfincs_adapter import SfincsAdapter
from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.hazard.event.eventset import EventSet
from flood_adapt.object_model.hazard.hazard_strategy import HazardStrategy
from flood_adapt.object_model.hazard.physical_projection import PhysicalProjection
from flood_adapt.object_model.interface.events import (
    Mode,
    RainfallSource,
    WindSource,
)
from flood_adapt.object_model.interface.measures import HazardType
from flood_adapt.object_model.interface.scenarios import ScenarioModel
from flood_adapt.object_model.io.timeseries import Timeseries
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
from flood_adapt.object_model.projection import Projection
from flood_adapt.object_model.site import Site
from flood_adapt.object_model.strategy import Strategy
from flood_adapt.object_model.utils import cd


class Hazard:
    """class holding all information related to the hazard of the scenario
    includes functions to generate generic timeseries for the hazard models
    and to run the hazard models
    """

    name: str
    database_input_path: Path
    mode: Mode
    event_set: EventSet
    physical_projection: PhysicalProjection
    hazard_strategy: HazardStrategy
    has_run: bool = False

    def __init__(
        self, scenario: ScenarioModel, database_input_path: Path, results_dir: Path
    ) -> None:
        self._mode: Mode
        self.simulation_paths: List[Path]
        self.simulation_paths_offshore: List[Path]
        self.event_list: list[Event] = []
        self.name = scenario.name
        self.results_dir = results_dir
        self.database_input_path = database_input_path
        self.set_event(
            scenario.event
        )  # also setting the mode (single_event or risk here)
        self.set_hazard_strategy(scenario.strategy)
        self.set_physical_projection(scenario.projection)
        self.site = Site.load_file(
            database_input_path.parent / "static" / "site" / "site.toml"
        )

        self.set_simulation_paths()

        self._set_sfincs_map_path(mode=self.event_mode)

        self.has_run = self.sfincs_has_run_check()

    @property
    def event_mode(self) -> Mode:
        return self._mode

    @event_mode.setter
    def event_mode(self, mode: Mode) -> None:
        self._mode = mode

    def _set_sfincs_map_path(self, mode: Mode) -> None:
        if mode == Mode.single_event:
            [self.sfincs_map_path] = self.simulation_paths

        elif mode == Mode.risk:
            self.sfincs_map_path = self.results_dir

    def set_simulation_paths(self) -> None:
        if self._mode == Mode.single_event:
            self.simulation_paths = [
                self.database_input_path.parent.joinpath(
                    "output",
                    "Scenarios",
                    self.name,
                    "Flooding",
                    "simulations",
                    self.site.attrs.sfincs.overland_model,
                )
            ]
            # Create a folder name for the offshore model (will not be used if offshore model is not created)
            self.simulation_paths_offshore = [
                self.database_input_path.parent.joinpath(
                    "output",
                    "Scenarios",
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
                    self.database_input_path.parent.joinpath(
                        "output",
                        "Scenarios",
                        self.name,
                        "Flooding",
                        "simulations",
                        subevent.attrs.name,
                        self.site.attrs.sfincs.overland_model,
                    )
                )
                # Create a folder name for the offshore model (will not be used if offshore model is not created)
                self.simulation_paths_offshore.append(
                    self.database_input_path.parent.joinpath(
                        "output",
                        "Scenarios",
                        self.name,
                        "Flooding",
                        "simulations",
                        subevent.attrs.name,
                        self.site.attrs.sfincs.offshore_model,
                    )
                )

    def sfincs_has_run_check(self) -> bool:
        """checks if the hazard has been already run"""
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

    def set_event(self, event_name: str) -> None:
        """Sets the actual Event template class list using the list of measure names
        Args:
            event_name (str): name of event used in scenario
        """
        event_set_path = (
            self.database_input_path / "events" / event_name / f"{event_name}.toml"
        )
        # set mode (probabilistic_set or single_event)
        self.event_mode = Event.get_mode(event_set_path)
        self.event_set = EventSet.load_file(event_set_path)

        if self._mode == Mode.single_event:
            self.event_set.event_paths = [event_set_path]
            self.probabilities = [1]

        elif self._mode == Mode.risk:
            self.event_set.event_paths = []
            subevents = self.event_set.attrs.subevent_name

            for subevent_name in subevents:
                event_path = (
                    self.database_input_path
                    / "events"
                    / event_name
                    / subevent_name
                    / f"{subevent_name}.toml"
                )
                self.event_set.event_paths.append(event_path)

        # parse event config file to get event template
        for event_path in self.event_set.event_paths:
            event = Event.load_file(event_path)
            self.event_list.append(event)
        self.event = self.event_list[0]
        # set event for single_event to be able to plot wl etc

    def set_physical_projection(self, projection: str) -> None:
        projection_path = (
            self.database_input_path / "Projections" / projection / f"{projection}.toml"
        )
        self.physical_projection = Projection.load_file(
            projection_path
        ).get_physical_projection()

    def set_hazard_strategy(self, strategy: str) -> None:
        strategy_path = (
            self.database_input_path / "Strategies" / strategy / f"{strategy}.toml"
        )
        self.hazard_strategy = Strategy.load_file(strategy_path).get_hazard_strategy()

    # no write function is needed since this is only used internally

    @staticmethod
    def get_event_object(event_path):
        mode = Event.get_mode(event_path)
        if mode == Mode.single_event:
            return Event.load_file(event_path)
        elif mode == Mode.risk:
            return EventSet.load_file(event_path)

    def preprocess_models(self):
        logging.info("Preparing hazard models...")
        # Preprocess all hazard model input

        self.preprocess_sfincs()
        # add other models here

    def run_models(self):
        for parent in reversed(self.results_dir.parents):
            if not parent.exists():
                os.mkdir(parent)
        if not self.results_dir.exists():
            os.mkdir(self.results_dir)
        logging.info("Running hazard models...")
        if not self.has_run:
            self.run_sfincs()

    def postprocess_models(self):
        logging.info("Post-processing hazard models...")
        # Postprocess all hazard model input
        self.postprocess_sfincs()
        # add other models here
        # WITHOUT A SFINCS FOLDER WE CANNOT READ sfincs_map.nc ANYMORE
        # remove simulation folders
        # if not self.site.attrs.sfincs.save_simulation:
        #     for simulation_path in self.simulation_paths:
        #         if os.path.exists(simulation_path.parent):
        #             try:
        #                 shutil.rmtree(
        #                     simulation_path.parent
        #                 )  # TODO cannot remove simulation because hydromt log file is still being used
        #             except WindowsError:
        #                 pass

    def run_sfincs(self):
        # Run new model(s)
        sfincs_exec = FloodAdapt_config.get_system_folder() / "sfincs" / "sfincs.exe"

        # results_dir = self.database_input_path.parent.joinpath(
        #     "output", "results", self.name
        # )
        for simulation_path in self.simulation_paths:
            with cd(simulation_path):
                sfincs_log = "sfincs.log"
                # with open(results_dir.joinpath(f"{self.name}.log"), "a") as log_handler:
                with open(sfincs_log, "a") as log_handler:
                    subprocess.run(sfincs_exec, stdout=log_handler)

        # Indicator that hazard has run
        self.__setattr__("has_run", True)

    def run_sfincs_offshore(self, ii: int):
        # Run offshore model(s)

        sfincs_exec = FloodAdapt_config.get_system_folder() / "sfincs" / "sfincs.exe"

        simulation_path = self.simulation_paths_offshore[ii]
        with cd(simulation_path):
            sfincs_log = "sfincs.log"
            with open(sfincs_log, "w") as log_handler:
                subprocess.run(sfincs_exec, stdout=log_handler)

    def preprocess_sfincs(
        self,
    ):
        base_path = self.database_input_path.parent
        path_in = base_path.joinpath(
            "static", "templates", self.site.attrs.sfincs.overland_model
        )
        logging.info("Preprocessing SFINCS model...")

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

            ## DOWNLOAD METEO ##
            if (
                self.event.attrs.overland.wind.source == WindSource.map
                or self.event.attrs.overland.rainfall.source == RainfallSource.map
            ):
                meteo_dir = self.database_input_path.parent.joinpath("output", "meteo")
                if not meteo_dir.is_dir():
                    os.mkdir(
                        self.database_input_path.parent.joinpath("output", "meteo")
                    )
                ds = self.event.download_meteo(
                    site=self.site, path=meteo_dir
                )  # =event_dir)
                ds = ds.rename({"barometric_pressure": "press"})
                ds = ds.rename({"precipitation": "precip"})
            else:
                ds = None

            ## WATER LEVELS ##
            # generate hazard water level bc incl SLR (in the offshore model these are already included)
            # returning wl referenced to MSL
            if not self.event.attrs.overland.gauged:  # synthetic
                logging.info("Preparing synthetic tide and surge for overland model...")
                # e.g. for synthetic events that provide water levels
                self.event.add_tide_and_surge_ts()
                # add water level offset due to historic SLR for synthetic event
                wl_ts = (
                    self.event.tide_surge_ts
                    + self.site.attrs.slr.vertical_offset.convert(
                        self.site.attrs.gui.default_length_units
                    ).value
                )
            else:  # gauged or produced by offshore model
                # water level offset due to historic SLR already included in observations
                logging.info(
                    "Using gauged or generated tide and surge for overland model..."
                )
                wl_ts = self.event.tide_surge_ts

            # In both cases, add SLR
            wl_ts[1] = (
                wl_ts[1]
                + self.physical_projection.attrs.sea_level_rise.convert(
                    self.site.attrs.gui.default_length_units
                ).value
            )
            # unit conversion to metric units (not needed for water levels coming from the offshore model, see below)
            conversion_factor = (
                UnitfulLength(1, self.site.attrs.gui.default_length_units)
                .convert(UnitTypesLength.meters)
                .value
            )
            self.wl_ts = conversion_factor * wl_ts

            ### OFFSHORE MODEL ###
            if self.event.attrs.offshore is not None:
                logging.info("Preparing offshore model to generate tide and surge...")
                self.preprocess_sfincs_offshore(ds=ds, ii=ii)
                # Run the actual SFINCS model
                logging.info("Running offshore model...")
                self.run_sfincs_offshore(ii=ii)
                # add wl_ts to self
                self.postprocess_sfincs_offshore(ii=ii)

                # turn off pressure correction at the boundaries because the effect of
                # atmospheric pressure is already included in the water levels from the
                # offshore model
                model.turn_off_bnd_press_correction()

            logging.info(
                "Adding water level boundary conditions to the overland flood model..."
            )
            # add difference between MSL (vertical datum of offshore nad backend in general) and overland model
            self.wl_ts += (
                (
                    self.site.attrs.water_level.msl.height
                    - self.site.attrs.water_level.localdatum.height
                )
                .convert(UnitTypesLength.meters)
                .value
            )
            model.add_wl_bc(self.wl_ts)

            ### RIVER DISCHARGE ###
            # ASSUMPTION: Order of the rivers is the same as the site.toml file
            self.event.add_river_discharge_ts(
                event_dir=event_dir, site_river=self.site.attrs.river
            )
            if self.event.dis_df is not None:
                logging.info(
                    "Adding RIVER discharge boundary conditions to the overland flood model..."
                )
                # convert to metric units
                conversion_factor = (
                    UnitfulDischarge(1, self.site.attrs.gui.default_discharge_units)
                    .convert(UnitTypesDischarge.cms)
                    .value
                )
                model.add_dis_bc(
                    list_df=conversion_factor * self.event.dis_df,
                    site_river=self.site.attrs.river,
                )

            ## NON-HURRICANE ##
            if self.event.attrs.offshore.hurricane is None:
                ## RAINFALL ##
                if self.event.attrs.overland.rainfall.source == RainfallSource.map:
                    logging.info(
                        "Adding gridded rainfall to the overland flood model..."
                    )
                    # add rainfall increase from projection and event, units area already conform with sfincs when downloaded
                    model.add_precip_forcing_from_grid(
                        ds=ds["precip"]
                        * self.physical_projection.attrs.rainfall_multiplier
                        * self.event.attrs.overland.rainfall.multiplier
                    )
                elif (
                    self.event.attrs.overland.rainfall.source
                    == RainfallSource.timeseries
                ):
                    logging.info(
                        "Adding rainfall timeseries to the overland flood model..."
                    )

                    conversion_factor_precip = (
                        UnitfulIntensity(
                            1.0, self.site.attrs.gui.default_intensity_units
                        )
                        .convert(UnitTypesIntensity.mm_hr)
                        .value
                    )

                    df = Timeseries(
                        self.event.attrs.overland.rainfall.timeseries
                    ).to_dataframe(
                        start_time=self.event.attrs.time.start_time,
                        end_time=self.event.attrs.time.end_time,
                    )
                    df = (
                        conversion_factor_precip
                        * df
                        * self.physical_projection.attrs.rainfall_multiplier
                        * self.event.attrs.overland.rainfall.multiplier
                    )

                    model.add_precip_forcing(timeseries=df)

                ## WIND ##
                if self.event.attrs.overland.wind.source == WindSource.map:
                    logging.info(
                        "Adding gridded wind field to the overland flood model..."
                    )
                    model.add_wind_forcing_from_grid(ds=ds)
                elif self.event.attrs.overland.wind.source == WindSource.timeseries:
                    logging.info(
                        "Adding wind timeseries to the overland flood model..."
                    )

                    df = pd.read_csv(
                        event_dir.joinpath(
                            self.event.attrs.overland.wind.timeseries_file
                        ),
                        index_col=0,
                        header=None,
                    )
                    df[1] = conversion_factor_precip * df[1]
                    df.index = pd.DatetimeIndex(df.index)
                    model.add_wind_forcing(timeseries=df)
                elif self.event.attrs.overland.wind.source == WindSource.constant:
                    logging.info("Adding constant wind to the overland flood model...")
                    # conversion factor to metric units
                    conversion_factor_wind = (
                        UnitfulVelocity(1.0, self.site.attrs.gui.default_velocity_units)
                        .convert(UnitTypesVelocity.mps)
                        .value
                    )
                    model.add_wind_forcing(
                        const_mag=self.event.attrs.overland.wind.constant_speed.value
                        * conversion_factor_wind,
                        const_dir=self.event.attrs.overland.wind.constant_direction.value,
                    )

            ## HURRICANE ##
            else:
                # Copy spw file also to nearshore folder
                logging.info(
                    "Adding wind field generated from hurricane track to the overland flood model..."
                )
                spw_name = "hurricane.spw"
                model.set_config_spw(spw_name=spw_name)
                if self.physical_projection.attrs.rainfall_multiplier != 0.0:
                    logging.warning(
                        "Rainfall increase from projection is not applied to hurricane events where the spatial rainfall is derived from the track variables."
                    )

            ## HAZARD MEASURES ##
            if self.hazard_strategy.measures is not None:
                for measure in self.hazard_strategy.measures:
                    measure_path = base_path.joinpath(
                        "input", "measures", measure.attrs.name
                    )
                    if measure.attrs.type == HazardType.floodwall:
                        logging.info("Adding floodwall to the overland flood model...")
                        model.add_floodwall(
                            floodwall=measure.attrs, measure_path=measure_path
                        )
                    if measure.attrs.type == HazardType.pump:
                        model.add_pump(pump=measure.attrs, measure_path=measure_path)
                    if (
                        measure.attrs.type == HazardType.greening
                        or measure.attrs.type == HazardType.total_storage
                        or measure.attrs.type == HazardType.water_square
                    ):
                        logging.info(
                            "Adding green infrastructure to the overland flood model..."
                        )
                        model.add_green_infrastructure(
                            green_infrastructure=measure.attrs,
                            measure_path=measure_path,
                        )

            ## OBSERVATION POINTS ##
            model.add_obs_points()
            logging.info("Adding observation points to the overland flood model...")

            # write sfincs model in output destination
            model.write_sfincs_model(path_out=self.simulation_paths[ii])

            # Write spw file to overland folder
            if self.event.attrs.offshore.hurricane is not None:
                shutil.copy2(
                    self.simulation_paths_offshore[ii].joinpath(spw_name),
                    self.simulation_paths[ii].joinpath(spw_name),
                )

            del model

    def preprocess_sfincs_offshore(self, ds: xr.DataArray, ii: int):
        """Preprocess offshore model to obtain water levels for boundary condition of the nearshore model

        Args:
            ds (xr.DataArray): DataArray with meteo information (downloaded using event.download_meteo())
            ii (int): Iterator for event set
        """
        # Determine folders for offshore model
        base_path = self.database_input_path.parent
        path_in_offshore = base_path.joinpath(
            "static", "templates", self.site.attrs.sfincs.offshore_model
        )
        if self.event_mode == Mode.risk:
            event_dir = (
                self.database_input_path
                / "events"
                / self.event_set.attrs.name
                / self.event.attrs.name
            )
        else:
            event_dir = self.database_input_path / "events" / self.event.attrs.name

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

        # Add wind
        # and if applicable pressure forcing from meteo data (historical_offshore) or spiderweb file (historical_hurricane).
        if self.event.attrs.offshore.hurricane is None:
            if self.event.attrs.offshore.wind.source == WindSource.map:
                offshore_model.add_wind_forcing_from_grid(ds=ds)
                offshore_model.add_pressure_forcing_from_grid(ds=ds["press"])

            elif self.event.attrs.offshore.wind.source == WindSource.timeseries:
                offshore_model.add_wind_forcing(
                    timeseries=event_dir.joinpath(
                        self.event.attrs.offshore.wind.timeseries_file
                    )
                )

            elif self.event.attrs.offshore.wind.source == WindSource.constant:
                offshore_model.add_wind_forcing(
                    const_mag=self.event.attrs.offshore.wind.constant_speed.value,
                    const_dir=self.event.attrs.offshore.wind.constant_direction.value,
                )
        else:
            spw_name = "hurricane.spw"
            offshore_model.set_config_spw(spw_name=spw_name)
            if event_dir.joinpath(spw_name).is_file():
                logging.info("Using existing hurricane meteo data.")
                # copy spw file from event directory to offshore model folder
                shutil.copy2(
                    event_dir.joinpath(spw_name),
                    self.simulation_paths_offshore[ii].joinpath(spw_name),
                )
            else:
                logging.info(
                    "Generating meteo input to the model from the hurricane track..."
                )
                offshore_model.add_spw_forcing(
                    historical_hurricane=self.event,
                    database_path=base_path,
                    model_dir=self.simulation_paths_offshore[ii],
                )
                # save created spw file in the event directory
                shutil.copy2(
                    self.simulation_paths_offshore[ii].joinpath(spw_name),
                    event_dir.joinpath(spw_name),
                )
                logging.info("Finished generating meteo data from hurricane track.")

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
        if self._mode == Mode.single_event:
            # Write flood-depth map geotiff
            self.write_floodmap_geotiff()
            self.plot_wl_obs()
            # Copy SFINCS output map to main folder
            # self.sfincs_map_path = self.results_dir.joinpath(f"floodmap_{self.name}.nc")
            # shutil.copyfile(
            #     self.simulation_paths[0].joinpath("sfincs_map.nc"), self.sfincs_map_path
            # )
        elif self._mode == Mode.risk:
            self.calculate_rp_floodmaps()
            # self.sfincs_map_path = []
            # self.calculate_floodfrequency_map()

    def plot_wl_obs(self):
        """Plot water levels at SFINCS observation points as html
        Only for single event scenarios
        """
        for sim_path in self.simulation_paths:
            # read SFINCS model
            model = SfincsAdapter(model_root=sim_path, site=self.site)

            df, gdf = model.read_zs_points()

            del model

            gui_units = UnitTypesLength(self.site.attrs.gui.default_length_units)

            conversion_factor = (
                UnitfulLength(1.0, UnitTypesLength.meters).convert(gui_units).value
            )

            for ii, col in enumerate(df.columns):
                # Plot actual thing
                fig = px.line(
                    df[col] * conversion_factor
                    + self.site.attrs.water_level.localdatum.height.convert(
                        gui_units
                    ).value  # convert to reference datum for plotting
                )

                # plot reference water levels
                fig.add_hline(
                    y=self.site.attrs.water_level.msl.height.convert(gui_units).value,
                    line_dash="dash",
                    line_color="#000000",
                    annotation_text="MSL",
                    annotation_position="bottom right",
                )
                if self.site.attrs.water_level.other:
                    for wl_ref in self.site.attrs.water_level.other:
                        fig.add_hline(
                            y=wl_ref.height.convert(gui_units).value,
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

                # check if event uses tide gauge data
                if self.event.attrs.overland.gauged:
                    # check if observation station has a tide gauge ID
                    # if yes to both download tide gauge data and add to plot
                    if isinstance(self.site.attrs.obs_point[ii].ID, int):
                        df_gauge = Event.download_wl_data(
                            station_id=self.site.attrs.obs_point[ii].ID,
                            start_time_str=self.event.attrs.time.start_time,
                            stop_time_str=self.event.attrs.time.end_time,
                            units=UnitTypesLength(gui_units),
                        )

                        fig.add_trace(
                            go.Scatter(
                                x=pd.DatetimeIndex(df_gauge.index),
                                y=df_gauge[1]
                                + self.site.attrs.water_level.msl.height.convert(
                                    gui_units
                                ).value,
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
            demfile = self.database_input_path.parent.joinpath(
                "static", "dem", self.site.attrs.dem.filename
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
            raise NotImplementedError(f"Cannot compare Hazard to {type(other)}.")
        test1 = self.event_list == other.event_list
        test2 = self.physical_projection == other.physical_projection
        test3 = self.hazard_strategy == other.hazard_strategy
        return test1 & test2 & test3

    def calculate_rp_floodmaps(self):
        """calculates flood risk maps from a set of (currently) SFINCS water level outputs,
        using linear interpolation, would be nice to make it more widely applicable and
        move the loading of the SFINCS results to self.postprocess_sfincs()
        generates return period water level maps in netcdf format to be used by FIAT
        generates return period water depth maps in geotiff format as product for users
        TODO: make this robust and more efficient for bigger datasets
        """

        floodmap_rp = self.site.attrs.risk.return_periods

        frequencies = self.event_set.attrs.frequency
        # adjust storm frequency for hurricane events
        if self.physical_projection.attrs.storm_frequency_increase != 0:
            storminess_increase = (
                self.physical_projection.attrs.storm_frequency_increase / 100.0
            )
            for ii, event in enumerate(self.event_list):
                if event.attrs.offshore.hurricane is not None:
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
            # fill nan values with minimum bed levels in each grid cell, np.interp cannot ignore nan values
            zs_stacked = xr.where(np.isnan(zs_stacked), zb, zs_stacked)
            zs_maps.append(zs_stacked)

            del sim

        # Create RP flood maps

        # 1a: make a table of all water levels and associated frequencies
        zs = xr.concat(zs_maps, pd.Index(frequencies, name="frequency"))
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
            demfile = self.database_input_path.parent.joinpath(
                "static", "dem", self.site.attrs.dem.filename
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
        # logging.info("Created geotiff file with flood frequency.")
        # print("Created geotiff file with flood frequency.", file=sys.stdout, flush=True)

        # outdata.FlushCache()  ##saves to disk!!
        # outdata = None
        # band = None
        # dem_ds = None
