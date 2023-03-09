from pathlib import Path
from typing import Optional

import tomli
from pydantic import BaseModel

from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.hazard.event.event_factory import EventFactory
from flood_adapt.object_model.hazard.event.synthetic import Synthetic
from flood_adapt.object_model.io.database_io import DatabaseIO


class AttrModel(BaseModel):  # TODO replace with ScenarioModel
    """BaseModel describing the expected variables and data types of the scenario"""

    name: str
    long_name: str
    event: str
    projection: str
    strategy: str


class EventTemplateModel:
    Synthetic: Synthetic


class Hazard:
    """class holding all information related to the hazard of the scenario
    includes functions to generate generic timeseries for the hazard models
    and to run the hazard models
    """

    attrs: AttrModel
    event_obj: Optional[EventTemplateModel]
    ensemble: Optional[EventTemplateModel]
    # physical_projection: PhysicalProjection
    # hazard_strategy: HazardStrategy

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

    #     self.physical_projection.load(
    #         str(
    #             Path(
    #                 DatabaseIO().projections_path,
    #                 projection,
    #                 "{}.toml".format(projection),
    #             )
    #         )
    #     )

    # def set_hazard_strategy(self, strategy: str):
    #     self.hazard_strategy.load(
    #         str(
    #             Path(DatabaseIO().strategies_path, strategy, "{}.toml".format(strategy))
    #         )
    #     )

    # no write function is needed since this is only used internally

    def calculate_rp_floodmaps(self, rp: list) -> Path:
        path_to_floodmaps = None
        return path_to_floodmaps

    def add_wl_ts(self):
        """adds total water level timeseries"""
        # generating total time series made of tide, slr and water level offset
        template = self.event_obj.attrs.template
        if template == "Synthetic" or template == "Historical_nearshore":
            self.event_obj.add_tide_ts()
            self.wl_ts = self.event_obj.tide_ts
            self.wl_ts["wl"] = (
                self.wl_ts["wl"]
                + self.event_obj.attrs.water_level_offset.convert_unit()
            )
            return self

    def run(self):
        ...
