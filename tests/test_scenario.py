from pathlib import Path
import pytest

test_database = Path().absolute() / 'tests' / 'test_database'

def test_scenario_class():
    from flood_adapt.object_model.scenario import Scenario

    test_scenario_toml = test_database / "charleston" / "input" / "scenarios" / "current_HUGO_no_measures" / "current_HUGO_no_measures.toml"
    assert test_scenario_toml.is_file()

    test_site_toml = test_database / "charleston" / "input" / "scenarios" / "current_HUGO_no_measures" / "current_HUGO_no_measures.toml"
    assert test_site_toml.is_file()

    test_scenario = Scenario()
    assert test_scenario.direct_impacts

    test_scenario.direct_impacts.configure(test_scenario_toml)

    # Check if all variables are read correctly from the site config file.
    assert test_scenario.direct_impacts.site_info.name == "charleston"
    assert test_scenario.direct_impacts.site_info.long_name == "Charleston, SC"
    assert test_scenario.direct_impacts.site_info.lat == 32.77
    assert test_scenario.direct_impacts.site_info.lon == -79.95
    assert test_scenario.direct_impacts.site_info.sfincs["cstype"] == "projected"
    assert test_scenario.direct_impacts.site_info.gui["tide_harmonic_amplitude"]["value"] == 3.0
    assert test_scenario.direct_impacts.site_info.dem["filename"] == "charleston_14m.tif"
    assert test_scenario.direct_impacts.site_info.fiat["aggregation_shapefiles"] == "subdivision.shp"
    assert test_scenario.direct_impacts.site_info.river["mean_discharge"]["units"] == "cfs"
    assert test_scenario.direct_impacts.site_info.obs_station["ID"] == 8665530
    assert test_scenario.direct_impacts.site_info.obs_station["mllw"]["value"] == 0.0

    