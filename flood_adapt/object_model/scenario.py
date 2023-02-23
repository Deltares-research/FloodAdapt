from flood_adapt.object_model.direct_impacts import DirectImpacts
from flood_adapt.object_model.site import SiteConfig
from flood_adapt.object_model.io.database_io import DatabaseIO


class Scenario:
    """The Scenario class containing all information on a single scenario."""
    def __init__(self):
        self.database = DatabaseIO()
        self.direct_impacts = DirectImpacts()
        self.site_info = SiteConfig(self.database.site_config_path)
