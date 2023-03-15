# import subprocess
# import sys
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from flood_adapt.integrator.sfincs_adapter import SfincsAdapter
from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.hazard.event.event_factory import EventFactory
from flood_adapt.object_model.hazard.event.synthetic import Synthetic
from flood_adapt.object_model.hazard.hazard_strategy import HazardStrategy
from flood_adapt.object_model.hazard.physical_projection import (
    PhysicalProjection,
)
from flood_adapt.object_model.io.database_io import DatabaseIO
from flood_adapt.object_model.projection import Projection

# from flood_adapt.object_model.scenario import ScenarioModel
from flood_adapt.object_model.strategy import Strategy


class ScenarioModel(BaseModel):
    """BaseModel describing the expected variables and data types of a scenario"""

    name: str
    long_name: str
    event: str
    projection: str
    strategy: str


class EventTemplateModel(Enum):
    Synthetic: Synthetic


class Hazard:
    """class holding all information related to the hazard of the scenario
    includes functions to generate generic timeseries for the hazard models
    and to run the hazard models
    """

    event: Optional[EventTemplateModel]
    # ensemble: Optional[EnsembleTemplateModel]
    physical_projection: Optional[PhysicalProjection]
    hazard_strategy: Optional[HazardStrategy]
    has_run_hazard: bool = False

    def __init__(self, scenario) -> None:
        self.set_event(scenario.direct_impacts.hazard.event)
        self.set_hazard_strategy(scenario.strategy)
        self.set_physical_projection(scenario.projection)

    def set_event(self, event: EventTemplateModel) -> None:
        """Sets the actual Event template class list using the list of measure names
        Args:
            event_name (str): name of event used in scenario
        """
        event_path = Path(
            DatabaseIO().events_path,
            event.attrs.name,
            "{}.toml".format(event.attrs.name),
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
        projection_path = Path(
            DatabaseIO().projections_path, projection, f"{projection}.toml"
        )
        self.physical_projection = Projection.load_file(
            projection_path
        ).get_physical_projection()

    def set_hazard_strategy(self, strategy: str) -> None:
        strategy_path = Path(DatabaseIO().strategies_path, strategy, f"{strategy}.toml")
        self.hazard_strategy = Strategy.load_file(strategy_path).get_hazard_strategy()

    # no write function is needed since this is only used internally

    def calculate_rp_floodmaps(self, rp: list):
        raise NotImplementedError

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

    def run_sfincs(self):
        # TODO: make path variable
        # path_on_n = Path(
        #     "n:/Projects/11207500/11207949/F. Other information/Test_data/database/charleston"
        # )
        path_on_n = Path(
            "c:/Users/winter_ga/Offline_Data/project_data/FloodAdapt/Test_data/database/charleston"
        )
        path_in = path_on_n.joinpath("static/templates/overland")
        run_folder_overland = path_on_n.joinpath(
            "output/simulations", self.attrs.name, "overland"
        )  # TODO: replace "overland" with overland_model  from Site object

        self.add_wl_ts()

        # Load overland sfincs model
        model = SfincsAdapter(model_root=path_in)

        # adjust timing of model
        model.set_timing()

        # Change water level boundary condition
        model.add_wl_bc(self.wl_ts)  # TODO not working

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
                    "..\..\..\..\..\..\..\system\sfincs\{}\sfincs.exe>sfincs_log.txt".format(
                        "sfincs20_AlpeDHuez_release"
                    )  # TODO read SFINCS version from Site object
                )
                f_out.write(bat_file)
        elif self.event.attrs.mode == "single_scenario":
            with open(run_folder_overland.joinpath("run.bat"), "w") as f_out:
                bat_file: str = (
                    "cd "
                    "%~dp0"
                    "\n"
                    "..\..\..\..\..\..\system\sfincs\{}\sfincs.exe>sfincs_log.txt".format(
                        "sfincs20_AlpeDHuez_release"
                    )
                )
                f_out.write(bat_file)

        ##TODO: fix this, it is neater and allows to writing to a log file
        # with subprocess.Popen(
        #     str(run_folder_overland.joinpath("run.bat")),
        #     shell=True,
        #     stdout=subprocess.PIPE,
        #     stderr=subprocess.PIPE,
        #     bufsize=1,
        #     universal_newlines=True,
        # ) as result:
        #     for line in result.stdout:
        #         print(
        #             "SFINCS overland model >>> {}\n".format(line[:-1]),
        #             end="",
        #             file=sys.stdout,
        #             flush=True,
        #         )  # process line here

        # if result.returncode != 0:
        #     raise subprocess.CalledProcessError(result.returncode, result.args)

        # Indicator that sfincs model has run
        self.__setattr__("has_run", True)
