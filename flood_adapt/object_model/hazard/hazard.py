from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

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
    ensemble: Optional[EventTemplateModel]
    physical_projection: Optional[PhysicalProjection]
    hazard_strategy: Optional[HazardStrategy]
    has_run_hazard: bool = False

    def __init__(self, scenario) -> None:
        self.set_event(scenario.event)
        self.set_hazard_strategy(scenario.strategy)
        self.set_physical_projection(scenario.projection)

    def set_event(self, event: str) -> None:
        """Sets the actual Event template class list using the list of measure names
        Args:
            event_name (str): name of event used in scenario
        """
        event_path = Path(DatabaseIO().events_path, event, "{}.toml".format(event))
        # set mode (probabilistic_set or single_scenario)
        mode = Event.get_mode(event_path)
        if mode == "single_scenario":
            # parse event config file to get event template
            template = Event.get_template(event_path)
            # use event template to get the associated event child class
            self.event = EventFactory.get_event(template).load_file(event_path)
        elif mode == "probabilistic_set":
            self.ensemble = None  # TODO: add Ensemble.load()

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
        pass
        # path_to_floodmaps = None
        # return path_to_floodmaps

    def add_wl_ts(self):
        """adds total water level timeseries"""
        # generating total time series made of tide, slr and water level offset
        template = self.event.attrs.template
        if template == "Synthetic" or template == "Historical_nearshore":
            self.event.add_tide_and_surge_ts()
            self.wl_ts = self.event.tide_surge_ts
            self.wl_ts["0:wl"] = (
                self.wl_ts["0:wl"]
                + self.event.attrs.water_level_offset.convert_to_meters()
            )  # TODO add slr
            return self

    # def run(self):
    #     self.__setattr__("has_run", True)
    #     ...
