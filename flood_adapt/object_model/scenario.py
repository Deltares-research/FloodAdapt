from flood_adapt.object_model.direct_impacts import DirectImpacts
from pathlib import Path

site_name_ = "charleston"  # This should be retrieved from somewhere else
database_path_ = str(Path().absolute() / 'tests' / 'test_database' / site_name_)  # This should be retrieved from somewhere else


class Scenario:
    """The Scenario class containing all information on a single scenario."""
    def __init__(self, database_path: str = database_path_, site_name: str = site_name_):
        self.direct_impacts = DirectImpacts(database_path, site_name)
