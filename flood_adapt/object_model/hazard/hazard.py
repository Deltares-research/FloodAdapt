from pathlib import Path
from flood_adapt.object_model.validate.config import (
    validate_content_config_file,
    validate_existence_config_file,
)
from flood_adapt.object_model.io.database_io import DatabaseIO
from flood_adapt.object_model.io.config_io import read_config, write_config
from flood_adapt.object_model.hazard.physical_projection.physical_projection import (
    PhysicalProjection,
)
from flood_adapt.object_model.hazard.hazard_strategy import HazardStrategy
from flood_adapt.object_model.hazard.event.event_factory import EventFactory


class Hazard:
    def __init__(self) -> None:
        self.set_default()

    def set_default(self):
        """Sets the default values of the Hazard class attributes"""
        self.name = ""
        self.long_name = ""
        self.mode = ""
        self.type = ""
        self.physical_projection = PhysicalProjection()
        self.hazard_strategy = HazardStrategy()

    def set_name(self, value):
        self.name = value

    def set_long_name(self, value):
        self.long_name = value

    def set_type(self, value):
        self.type = value

    def set_physical_projection(self, projection):
        self.physical_projection.load(
            str(
                Path(
                    DatabaseIO().projections_path,
                    projection,
                    "{}.toml".format(projection),
                )
            )
        )

    def set_hazard_strategy(self, strategy: str):
        self.hazard_strategy.load(
            str(
                Path(DatabaseIO().strategies_path, strategy, "{}.toml".format(strategy))
            )
        )

    def set_event(self, event):
        """Sets the actual Measure class list using the list of measure names
        Args:
            measures (list): list of measures names
        """
        event_path = str(Path(DatabaseIO().events_path, event, "{}.toml".format(event)))
        # set type of event (probabilistic_set or single_scenario)
        self.set_type(read_config(event_path)["type"])
        if self.type == "single_scenario":
            # parse event config file to get event template
            template = read_config(event_path)["template"]
            # use type of measure to get the associated measure subclass
            self.event = EventFactory.get_event(template).load(event_path)
        elif self.type == "probabilistic_set":
            self.ensemble = None  # TODO: add Ensemble.load()

    def set_values(self, config_file_path: str = None):
        self.config_file = config_file_path
        if validate_existence_config_file(self.config_file):
            self.config = read_config(self.config_file)

        if validate_content_config_file(self.config, self.config_file, []):
            self.set_name(self.config["name"])
            self.set_long_name(self.config["long_name"])
            self.set_physical_projection(self.config["projection"])
            self.set_hazard_strategy(self.config["strategy"])
            self.set_event(self.config["event"])
        return self

    # no write function is needed since this is only used internally

    def calculate_rp_floodmaps(self, rp: list) -> str:
        path_to_floodmaps = None
        return path_to_floodmaps
