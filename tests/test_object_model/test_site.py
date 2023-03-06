from pathlib import Path

test_database = Path().absolute() / "tests" / "test_database"


def test_read_site_toml():
    from flood_adapt.object_model.site import SiteConfig

    test_toml = test_database / "charleston" / "static" / "site" / "charleston.toml"
    assert test_toml.is_file()

    test_data = SiteConfig(config_path=test_toml)

    assert test_data
    assert test_data.name == "charleston"
    assert test_data.long_name == "Charleston, SC"
    assert test_data.lat == 32.77
    assert test_data.lon == -79.95
    assert test_data.sfincs["cstype"] == "projected"
    assert test_data.gui["tide_harmonic_amplitude"]["value"] == 3.0
    assert test_data.dem["filename"] == "charleston_14m.tif"
    assert test_data.fiat["aggregation_shapefiles"] == "subdivision.shp"
    assert test_data.river["mean_discharge"]["units"] == "cfs"
    assert test_data.obs_station["ID"] == 8665530
    assert test_data.obs_station["mllw"]["value"] == 0.0
