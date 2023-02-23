from pathlib import Path

from flood_adapt.object_model.io.config_io import read_config, write_config
from flood_adapt.object_model.hazard.physical_projection.physical_projection import PhysicalProjection
from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.hazard.event.synthetic import Synthetic
# from flood_adapt.object_model.hazard.event.hurricane import Hurricane
# from flood_adapt.object_model.hazard.event.historical_offshore import HistoricalOffshore
# from flood_adapt.object_model.hazard.event.historical_nearshore import HistoricalNearshore
# from flood_adapt.object_model.hazard.hazard_strategy.hazard_strategy import HazardStrategy
from flood_adapt.object_model.validate.config import validate_content_config_file, validate_existence_config_file

class Hazard:
    def __init__(self, database_path: str = None) -> None:
        self.set_default()
        if not self.database_path:
            self.database_path = str(Path(self.config_file).parents[3])

    def set_default(self):
        """ Sets the default values of the Hazard class attributes
        """
        self.name = ""
        self.long_name = ""
        self.mode = ""
        self.event = None
        self.ensemble = None
        self.physical_projection = PhysicalProjection()
        # self.hazard_strategy = HazardStrategy()
        self.mandatory_keys = ["name", "long_name", "mode", "event", "ensemble", "physical_projection"] #, "hazard_strategy"]

    def set_name(self, value):
        self.name = value
    
    def set_long_name(self, value):
        self.long_name = value

    def set_physical_projection(self, projection):
        projection_path = str(Path(self.database_path, "input", "projections", projection, "{}.toml".format(projection)))
        self.physical_projection = PhysicalProjection.load(projection_path)

    def set_event(self, event):
        """ Sets the actual Measure class list using the list of measure names
        Args:
            measures (list): list of measures names
        """
        event_path = str(Path(self.database_path, "input", "events", event, "{}.toml".format(event)))
        #         # parse event config file to get type of event
        template = read_config(event_path)["template"]
        # use type of measure to get the associated measure subclass
        self.event = event_parser(template).load(event_path)

    # def set_hazard_strategy(self, strategy):
    #     strategy_path = str(Path(self.database_path, "input", "strategies", strategy, "{}.toml".format(strategy)))
    #     self.hazard_strategy = HazardStrategy.load(strategy_path)
    
    def set_values(self, config_file: str = None):
        self.config_file = config_file
        if validate_existence_config_file(config_file):
            config = read_config(self.inputfile)

        if validate_content_config_file(config, config_file, self.mandatory_keys):
            self.set_name(config["name"])
            self.set_long_name(config["long_name"])
            self.set_physical_projection(config["projection"])
            self.set_event(config["event"])
            # self.set_hazard_strategy(config["strategy"])

    # no write function is needed since this is only used internally

    def calculate_rp_floodmaps(self, rp: list(int)) -> str:
        path_to_floodmaps = None
        return path_to_floodmaps


def event_parser(template: str) -> Event:
    """ Simple parser to get the respective Event subclass from the template variable in the config file
    Args:
        type (str): name of Event type
    Returns:
        Event: Event child class
    """
    if template == "synthetic":
        return Synthetic  
    # elif template == "Historical - hurricane":
    #     return Hurricane  
    # elif template == "Historical - forced by offshore wind and tide":
    #     return HistoricalOffshore  
    # elif template == "Historical - forced by observed nearshore water levels":
    #     return HistoricalNearshore 