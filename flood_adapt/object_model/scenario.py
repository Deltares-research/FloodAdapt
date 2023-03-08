from pathlib import Path

from flood_adapt.object_model.direct_impacts import DirectImpacts
from flood_adapt.object_model.io.database_io import DatabaseIO
from flood_adapt.object_model.site import SiteConfig


class Scenario:
    """The Scenario class containing all information on a single scenario."""

    def __init__(self):
        self.direct_impacts = DirectImpacts()
        self.site_info = SiteConfig(DatabaseIO().site_config_path)

    def load(self, scenario: str):
        self.direct_impacts.load(
            str(Path(DatabaseIO().scenarios_path, scenario, "{}.toml".format(scenario)))
        )
        return self
