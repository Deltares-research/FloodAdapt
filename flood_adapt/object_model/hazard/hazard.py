from enum import Enum
from pathlib import Path
from typing import Optional

import tomli
import sys
import subprocess
from pydantic import BaseModel

from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.hazard.event.event_factory import EventFactory
from flood_adapt.object_model.hazard.event.synthetic import Synthetic
from flood_adapt.object_model.hazard.hazard_strategy import HazardStrategy
from flood_adapt.object_model.hazard.physical_projection import (
    PhysicalProjection,
)
from flood_adapt.object_model.io.database_io import DatabaseIO
from flood_adapt.integrator.sfincs_adapter import SfincsAdapter


class AttrModel(BaseModel):  # TODO replace with ScenarioModel
    """BaseModel describing the expected variables and data types of the scenario"""

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

    attrs: AttrModel
    event_obj: Optional[EventTemplateModel]
    ensemble: Optional[EventTemplateModel]
    physical_projection: Optional[PhysicalProjection]
    hazard_strategy: Optional[HazardStrategy]
    has_run_hazard: bool = False

    # def __init__(self, scenario_path: Path) -> None:
    #     pass

    @staticmethod
    def load_file(filepath: Path):
        """create Hazard from toml file"""

        obj = Hazard()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = AttrModel.parse_obj(toml)
        obj.set_event(obj.attrs.event)
        # obj.set_physical_projection(obj)
        # obj.set_hazard_strategy(obj)
        return obj

    def set_event(self, event_name: str):
        """Sets the actual Event template class list using the list of measure names
        Args:
            event_name (str): name of event used in scenario
        """
        event_path = Path(
            DatabaseIO().events_path, event_name, "{}.toml".format(event_name)
        )
        # set mode (probabilistic_set or single_scenario)
        mode = Event.get_mode(event_path)
        if mode == "single_scenario":
            # parse event config file to get event template
            template = Event.get_template(event_path)
            # use event template to get the associated event child class
            self.event_obj = EventFactory.get_event(template).load_file(event_path)
        elif mode == "probabilistic_set":
            self.ensemble = None  # TODO: add Ensemble.load()

    # def set_physical_projection(self, projection):
    #     self.physical_projection.load_file(
    #         str(
    #             Path(
    #                 DatabaseIO().projections_path,
    #                 projection,
    #                 "{}.toml".format(projection),
    #             )
    #         )
    #     )

    # def set_hazard_strategy(self, strategy: str):
    #     self.hazard_strategy.load_file(
    #         str(
    #             Path(DatabaseIO().strategies_path, strategy, "{}.toml".format(strategy))
    #         )
    #     )

    # no write function is needed since this is only used internally

    def calculate_rp_floodmaps(self, rp: list) -> Path:
        ...
        # path_to_floodmaps = None
        # return path_to_floodmaps

    def add_wl_ts(self):
        """adds total water level timeseries"""
        # generating total time series made of tide, slr and water level offset
        template = self.event_obj.attrs.template
        if template == "Synthetic" or template == "Historical_nearshore":
            self.event_obj.add_tide_and_surge_ts()
            self.wl_ts = self.event_obj.tide_surge_ts
            self.wl_ts["0:wl"] = (
                self.wl_ts["0:wl"]
                + self.event_obj.attrs.water_level_offset.convert_to_meters()
            )  # TODO add slr
            return self

    def run(self):

        #TODO: make path variable
        path_in = Path('n:\Projects\11207500\11207949\F. Other information\Test_data\database\charleston\static\templates\overland')
        run_folder_overland = Path('n:\Projects\11207500\11207949\F. Other information\Test_data\database\charleston\output\simulations\test')
               
        self.add_wl_ts()

        #Load overland sfincs model
        sf_model = SfincsAdapter.load_overland_sfincs_model(model_root=path_in)

        #Change water level bounary condition
        sf_model.add_wl_bc(self.wl_ts)

        #write sfincs model in output destination
        sf_model.write_sfincs_model(path_out=run_folder_overland)

        #Run new model (create batch file and run it)
        if self.event_obj.attrs.mode:  # adjust relative path to SFINCS executable for ensemble run (additional folder depth)
            with open(run_folder_overland.join("run.bat"), "w") as f_out:
                bat_file: str = "cd ""%~dp0""\n""..\..\..\..\..\..\..\system\sfincs\{}\sfincs.exe".format("sfincs20_AlpeDHuez_release")
                f_out.write(bat_file)
        else:
            with open(run_folder_overland.join("run.bat"), 'w') as f_out:
                bat_file: str = "cd ""%~dp0""\n""..\..\..\..\..\..\system\sfincs\{}\sfincs.exe".format("sfincs20_AlpeDHuez_release")
                f_out.write(bat_file)

        with subprocess.Popen(run_folder_overland.join("run.bat"), stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1, universal_newlines=True) as result:
            for line in result.stdout:
                print('SFINCS overland model >>> {}\n'.format(line[:-1]), end='', file=sys.stdout, flush=True)  # process line here
        
        if result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, result.args)

        #Indicator that sfincs model has run
        self.__setattr__("has_run", True)
