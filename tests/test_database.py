from pathlib import Path

from flood_adapt.dbs_controller import Database
from flood_adapt.object_model.site import Site

test_database_path = Path().absolute() / "tests" / "test_database"
test_site_name = "Charleston"


def test_database_controller():
    dbs = Database(test_database_path, test_site_name)

    assert isinstance(dbs.site, Site)


def test_projection_interp_slr():
    dbs = Database(test_database_path, test_site_name)

    slr = dbs.interp_slr("ssp245", 2075)

    assert slr.value > 0.3
    assert slr.value < 0.4
    assert slr.units == "meters"


def test_projection_plot_slr():
    dbs = Database(test_database_path, test_site_name)
    html_file_loc = dbs.plot_slr_scenarios()

    print(html_file_loc)
    assert Path(html_file_loc).is_file()
