from pathlib import Path

from flood_adapt.dbs_controller import Database
from flood_adapt.object_model.site import Site

test_database_path = Path().absolute() / "tests" / "test_database"
test_site_name = "Charleston"


def test_database_controller():
    dbs = Database(test_database_path, test_site_name)

    assert isinstance(dbs.site, Site)
