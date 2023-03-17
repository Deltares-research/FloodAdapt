# import subprocess
# import sys
from enum import Enum
from pathlib import Path
from typing import Optional

from flood_adapt.integrator.sfincs_adapter import SfincsAdapter
from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.hazard.event.event_factory import EventFactory
from flood_adapt.object_model.hazard.event.synthetic import Synthetic
from flood_adapt.object_model.hazard.hazard_strategy import HazardStrategy
from flood_adapt.object_model.hazard.physical_projection import (
    PhysicalProjection,
)
from flood_adapt.object_model.interface.scenarios import ScenarioModel
from flood_adapt.object_model.projection import Projection
from flood_adapt.object_model.site import SiteModel

# from flood_adapt.object_model.scenario import ScenarioModel
from flood_adapt.object_model.strategy import Strategy


class EventTemplateModel(Enum):
    Synthetic: Synthetic


class Hazard:
    """class holding all information related to the hazard of the scenario
    includes functions to generate generic timeseries for the hazard models
    and to run the hazard models
    """

    name: str
    database_input_path: Path
    event: Optional[EventTemplateModel]
    ensemble: Optional[EventTemplateModel]
    physical_projection: Optional[PhysicalProjection]
    hazard_strategy: Optional[HazardStrategy]
    has_run_hazard: bool = False

    def __init__(self, scenario: ScenarioModel, database_input_path: Path) -> None:
        self.name = scenario.name
        self.database_input_path = database_input_path
        self.set_event(scenario.event)
        self.set_hazard_strategy(scenario.strategy)
        self.set_physical_projection(scenario.projection)

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
        """adds total water level timeseries"""
        # generating total time series made of tide, slr and water level offset
        template = self.event.attrs.template
        if template == "Synthetic" or template == "Historical_nearshore":
            self.event.add_tide_and_surge_ts()
            self.wl_ts = self.event.tide_surge_ts
            self.wl_ts[1] = (
                self.wl_ts[1] + self.event.attrs.water_level_offset.convert_to_meters()
            )  # TODO add slr
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

    def run_sfincs(self, site=SiteModel):
        # TODO: make path variable
        # path_on_n = Path(
        #     "n:/Projects/11207500/11207949/F. Other information/Test_data/database/charleston"
        # )
        path_on_n = Path(
            "c:/Users/winter_ga/Offline_Data/project_data/FloodAdapt/Test_data/database/charleston"
        )
        path_in = path_on_n.joinpath(
            "static/templates", site.attrs.sfincs.overland_model
        )
        run_folder_overland = path_on_n.joinpath(
            "output/simulations", self.name, site.attrs.sfincs.overland_model
        )  # TODO: replace "overland" with overland_model  from Site object

        self.add_wl_ts()

        # Load overland sfincs model
        model = SfincsAdapter(model_root=path_in)

        # adjust timing of model
        model.set_timing(self.event.attrs)

        # Change water level boundary condition
        model.add_wl_bc(self.wl_ts)

        # write sfincs model in output destination
        model.write_sfincs_model(path_out=run_folder_overland)

        # Run new model (create batch file and run it)
        # create batch file to run SFINCS, adjust relative path to SFINCS executable for ensemble run (additional folder depth)
        if self.event.attrs.mode == "risk":
            with open(run_folder_overland.joinpath("run.bat"), "w") as f_out:
                bat_file: str = (
                    "cd "
                    "%~dp0"
                    "\n"
                    f"..\..\..\..\..\..\..\system\sfincs\{site.attrs.sfincs.version}\sfincs.exe>sfincs_log.txt"
                )
                f_out.write(bat_file)
        elif self.event.attrs.mode == "single_scenario":
            with open(run_folder_overland.joinpath("run.bat"), "w") as f_out:
                bat_file: str = (
                    "cd "
                    "%~dp0"
                    "\n"
                    f"..\..\..\..\..\..\system\sfincs\{site.attrs.sfincs.version}\sfincs.exe>sfincs_log.txt"
                )
                f_out.write(bat_file)

        # Indicator that sfincs model has run
        self.__setattr__("has_run", True)
