from pathlib import Path

from flood_adapt.object_model.direct_impact.impact_strategy import ImpactStrategy
from flood_adapt.object_model.direct_impact.socio_economic_change import (
    SocioEconomicChange,
)
from flood_adapt.object_model.hazard.hazard import Hazard
from flood_adapt.object_model.io.config_io import read_config, write_config
from flood_adapt.object_model.io.database_io import DatabaseIO
from flood_adapt.object_model.validate.config import (
    validate_content_config_file,
    validate_existence_config_file,
)


class DirectImpacts:
    """The Direct Impact class containing all information on a single direct impact scenario."""

    def __init__(self):
        self.name = ""
        self.long_name = ""
        self.run_type = "event"  # event for a single event and "risk" for a probabilistic event set and risk calculation
        self.has_run_hazard = False
        self.has_run_direct_impact = False
        self.flood_map_path = ""  # To be determined what type this object is, depending on how it will get it from the Events class.
        self.result_path = ""
        self.mandatory_keys = ["name", "long_name", "projection", "event", "strategy"]

    def write(self):
        write_config(
            self.config, "path to write to"
        )  # this is a placeholder for the function to be filled

    def set_name(self, value: str):
        self.name = value

    def set_long_name(self, value: str):
        self.long_name = value

    def set_run_type(self, value: str):
        self.run_type = value

    def set_has_run_hazard(self, value: bool):
        self.has_run_hazard = value

    def set_has_run_direct_impact(self, value: bool):
        self.has_run_direct_impact = value

    def set_flood_map_path(self, value: str):
        self.flood_map_path = value

    def set_result_path(self, value: str):
        self.result_path = value

    def set_socio_economic_change(self, projection: str):
        self.socio_economic_change = SocioEconomicChange().load(
            str(
                Path(
                    DatabaseIO().projections_path,
                    projection,
                    "{}.toml".format(projection),
                )
            )
        )

    def set_impact_strategy(self, strategy: str):
        self.impact_strategy = ImpactStrategy().load(
            str(
                Path(DatabaseIO().strategies_path, strategy, "{}.toml".format(strategy))
            )
        )

    def set_hazard(self, scenario_config: str):
        self.hazard = Hazard().set_values(scenario_config)

    def load(self, config_file_path: str):
        self.config_file = config_file_path
        if validate_existence_config_file(self.config_file):
            self.config = read_config(self.config_file)

        if validate_content_config_file(
            self.config, self.config_file, self.mandatory_keys
        ):
            self.set_name(self.config["name"])
            self.set_long_name(self.config["long_name"])

        self.set_socio_economic_change(self.config["projection"])
        self.set_impact_strategy(self.config["strategy"])
        self.set_hazard(config_file_path)
