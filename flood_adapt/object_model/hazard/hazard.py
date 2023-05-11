import subprocess
from pathlib import Path
from typing import Optional

from flood_adapt.integrator.sfincs_adapter import SfincsAdapter
from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.hazard.event.event_factory import EventFactory
from flood_adapt.object_model.hazard.hazard_strategy import HazardStrategy
from flood_adapt.object_model.hazard.physical_projection import PhysicalProjection
from flood_adapt.object_model.hazard.utils import cd
from flood_adapt.object_model.interface.scenarios import ScenarioModel
from flood_adapt.object_model.projection import Projection
from flood_adapt.object_model.site import Site
from flood_adapt.object_model.strategy import Strategy


class Hazard:
    """class holding all information related to the hazard of the scenario
    includes functions to generate generic timeseries for the hazard models
    and to run the hazard models
    """

    name: str
    database_input_path: Path
    event: Optional[Event]
    ensemble: Optional[Event]
    physical_projection: PhysicalProjection
    hazard_strategy: HazardStrategy
    has_run: bool = False

    def __init__(self, scenario: ScenarioModel, database_input_path: Path) -> None:
        self.name = scenario.name
        self.database_input_path = database_input_path
        self.set_event(scenario.event)
        self.set_hazard_strategy(scenario.strategy)
        self.set_physical_projection(scenario.projection)
        self.site = Site.load_file(
            database_input_path.parent / "static" / "site" / "site.toml"
        )
        self.simulation_path = database_input_path.parent.joinpath(
            "output", "simulations", self.name
        )
        self.has_run = self.sfincs_has_run_check()

    def sfincs_has_run_check(self):
        sfincs_path = self.simulation_path
        test1 = Path(sfincs_path).joinpath("sfincs_map.nc").exists()

        sfincs_log = Path(sfincs_path).joinpath("sfincs.log")

        if sfincs_log.exists():
            with open(sfincs_log) as myfile:
                if "Simulation finished" in myfile.read():
                    test2 = True
                else:
                    test2 = False
        else:
            test2 = False

        return (test1) & (test2)

    def set_event(self, event: str) -> None:
        """Sets the actual Event template class list using the list of measure names
        Args:
            event_name (str): name of event used in scenario
        """
        event_path = (
            self.database_input_path / "events" / event / "{}.toml".format(event)
        )
        # set mode (probabilistic_set or single_scenario)
        mode = Event.get_mode(event_path)
        if mode == "single_scenario":
            # parse event config file to get event template
            template = Event.get_template(event_path)
            # use event template to get the associated event child class
            self.event = EventFactory.get_event(template).load_file(event_path)
        elif mode == "probabilistic_set":
            raise NotImplementedError

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

    def calculate_rp_floodmaps(self, rp: list):
        raise NotImplementedError
        # path_to_floodmaps = None
        # return path_to_floodmaps

    def add_wl_ts(self):
        """adds total water level timeseries to hazard object"""
        # generating total time series made of tide, slr and water level offset,
        # only for Synthetic and historical from nearshore
        if self.event.attrs.template == "Synthetic":
            self.event.add_tide_and_surge_ts()
            self.wl_ts = self.event.tide_surge_ts
        elif self.event.attrs.template == "Historical_nearshore":
            wl_df = self.event.tide_surge_ts
            self.wl_ts = wl_df
        # In both cases add the slr and offset
        self.wl_ts[1] = (
            self.wl_ts[1]
            + self.event.attrs.water_level_offset.convert("meters")
            + self.physical_projection.attrs.sea_level_rise.convert("meters")
        )
        return self

    def add_discharge(self):
        """adds discharge timeseries to hazard object"""
        # constant for all event templates, additional: shape for Synthetic or timeseries for all historic
        self.event.add_dis_ts()
        self.dis_ts = self.event.dis_ts
        return self

    @staticmethod
    def get_event_object(event_path):  # TODO This could be used above as well?
        mode = Event.get_mode(event_path)
        if mode == "single_scenario":
            # parse event config file to get event template
            template = Event.get_template(event_path)
            # use event template to get the associated event child class
            return EventFactory.get_event(template).load_file(event_path)
        elif mode == "probabilistic_set":
            return None  # TODO: add Ensemble.load()

    def run_models(self):
        self.run_sfincs()

        # Indicator that hazard has run
        self.__setattr__("has_run", True)

    def run_sfincs(self):
        input_path = self.database_input_path.parent
        path_in = input_path.joinpath(
            "static", "templates", self.site.attrs.sfincs.overland_model
        )
        path_in_offshore = input_path.joinpath(
            "static", "templates", self.site.attrs.sfincs.offshore_model
        )
        event_dir = (
            self.database_input_path
            / "events"
            / self.event.attrs.name
        )
        sfincs_exec = (
            self.database_input_path.parents[2]
            / "system"
            / "sfincs"
            / self.site.attrs.sfincs.version
            / "sfincs.exe"
        )

        # Load overland sfincs model
        model = SfincsAdapter(model_root=path_in)

        # adjust timing of model
        model.set_timing(self.event.attrs)

        # Download meteo files if necessary
        if (
            self.event.attrs.wind.source == "map"
            or self.event.attrs.rainfall.source == "map"
        ):
            ds = self.event.download_meteo(site=self.site, path=event_dir)

        # Generate and change water level boundary condition
        template = self.event.attrs.template
        if template == "Synthetic" or template == "Historical_nearshore":
            self.add_wl_ts()
            model.add_wl_bc_from_ts(self.wl_ts)
        elif template == "Historical_offshore":
            # Use offshore model to derive water level boundary conditions for overland model

            # Initiate offshore model
            offshore_model = SfincsAdapter(model_root=path_in_offshore)

            # Set timing of offshore model (same as overland model)
            offshore_model.set_timing(self.event.attrs)

            # set wl of offshore model
            offshore_model.add_bzs_from_bca(self.event.attrs)

            # Add wind and if applicable pressure forcing from files.
            if self.event.attrs.wind.source == "map":
                offshore_model.add_wind_forcing_from_grid(
                    wind_u=ds["wind_u"], wind_v=ds["wind_v"]
                )
                offshore_model.add_pressure_forcing_from_grid(press=ds["barometric_pressure"])
            elif self.event.attrs.wind.source == "timeseries":
                offshore_model.add_wind_forcing(
                    timeseries=event_dir.joinpath("wind.csv")
                )
            elif self.event.attrs.wind.source == "constant":
                offshore_model.add_wind_forcing(
                    const_mag=self.event.attrs.wind.constant_speed.value,
                    const_dir=self.event.attrs.wind.constant_direction.value,
                )

            # write sfincs model in output destination
            offshore_model.write_sfincs_model(
                path_out=self.simulation_path.joinpath(
                    self.site.attrs.sfincs.offshore_model
                )
            )

            # Run the offshore model
            with cd(
                self.simulation_path.joinpath(self.site.attrs.sfincs.offshore_model)
            ):
                sfincs_log = "sfincs.log"
                with open(sfincs_log, "w") as log_handler:
                    subprocess.run(sfincs_exec, stdout=log_handler)

            # take his results from offshore model as input for wl bnd
            wl_df = offshore_model.get_wl_df_from_offshore_his_results()
            model.add_wl_bc(wl_df)

        elif template == "Hurricane":
            raise NotImplementedError
            

        # Generate and change discharge boundary condition
        self.add_discharge()
        model.add_dis_bc(self.dis_ts)

        # Generate and add rainfall boundary condition
        if self.event.attrs.rainfall.source == "map":
            model.add_precip_forcing_from_grid(precip=ds["precipitation"])
        elif self.event.attrs.rainfall.source == "timeseries":
            model.add_precip_forcing(timeseries=event_dir.joinpath("rainfall.csv"))
        elif self.event.attrs.wind.source == "constant":
            model.add_precip_forcing(
                const_precip=self.event.attrs.rainfall.constant_intensity
            )

        # Generate and add wind boundary condition
        if self.event.attrs.wind.source == "map":
            model.add_wind_forcing_from_grid(wind_u=ds["wind_u"], wind_v=ds["wind_v"])
        elif self.event.attrs.wind.source == "timeseries":
            model.add_wind_forcing(timeseries=event_dir.joinpath("wind.csv"))
        elif self.event.attrs.wind.source == "constant":
            model.add_wind_forcing(
                const_mag=self.event.attrs.wind.constant_speed.value,
                const_dir=self.event.attrs.wind.constant_direction.value,
            )

        # Add floodwall if included
        # if self.measure.floodwall is not None:  # TODO Gundula: fix met add_floodwall
        #     pass

        # write sfincs model in output destination
        model.write_sfincs_model(
            path_out=self.simulation_path.joinpath(
                self.site.attrs.sfincs.overland_model
            )
        )

        # Run new model (create batch file and run it)
        # create batch file to run SFINCS, adjust relative path to SFINCS executable for ensemble run (additional folder depth)
        with cd(self.simulation_path.joinpath(self.site.attrs.sfincs.overland_model)):
            sfincs_log = "sfincs.log"
            with open(sfincs_log, "w") as log_handler:
                subprocess.run(sfincs_exec, stdout=log_handler)

    def __eq__(self, other):
        if not isinstance(other, Hazard):
            # don't attempt to compare against unrelated types
            return NotImplemented
        test1 = self.event == other.event
        test2 = self.physical_projection == other.physical_projection
        test3 = self.hazard_strategy == other.hazard_strategy
        return test1 & test2 & test3
